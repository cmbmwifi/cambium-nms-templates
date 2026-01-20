#!/usr/bin/env python3
"""
Cambium Fiber OLT SSH JSON getter.

Author: Joshaven Potter
Version: 0.1.0
Date: 2025-11-24
"""

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union


@dataclass(frozen=True)
class OLTRequest:
    host: str
    password: str


@dataclass(frozen=True)
class CachePolicy:
    path: str
    ttl_seconds: int
    enabled: bool
    host: str


class DebugLog:
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def emit(self, message: str) -> None:
        if self.enabled:
            print(message, file=sys.stderr)


class OLTOutput:
    prompt_prefix = re.compile(r"<.*?#")
    ansi = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
    json_block = re.compile(r"\{.*\}", re.S)

    def __init__(self, debug: DebugLog):
        self.debug = debug

    def to_json_text(self, raw: str) -> str:
        cleaned = self._strip_noise(self._strip_prompts(self._strip_ansi(raw)))
        match = self.json_block.search(cleaned)
        if not match:
            # Show more context in error message
            preview = cleaned[:500] if len(cleaned) <= 500 else cleaned[:500] + "..."
            self.debug.emit(f"OLT output (after cleaning): {preview}")
            raise ValueError(f"no JSON found in OLT output (got {len(cleaned)} bytes after cleaning)")
        return match.group(0)

    def _strip_ansi(self, text: str) -> str:
        return self.ansi.sub("", text)

    def _strip_prompts(self, text: str) -> str:
        return "\n".join(self.prompt_prefix.sub("", ln) for ln in text.splitlines())

    def _strip_noise(self, text: str) -> str:
        lines = [ln.rstrip() for ln in text.splitlines()]
        lines = [ln for ln in lines if ln.strip() and "Warning: Input is not a terminal" not in ln]
        return "\n".join(self._drop_leading_banner(lines)).strip()

    def _drop_leading_banner(self, lines: Sequence[str]) -> Sequence[str]:
        for i, ln in enumerate(lines):
            if ln.lstrip().startswith("{") or ln.lstrip().startswith("["):
                return lines[i:]
        return lines


class OLTTransport:
    def __init__(self, output: OLTOutput, debug: DebugLog):
        self.output = output
        self.debug = debug

    _int_re = re.compile(r"^-?\d+$")
    _float_re = re.compile(r"^-?\d+\.\d+$")

    def _coerce_numbers(self, obj):
        """
        Recursively walk JSON and convert numeric-looking strings to int/float.
        Also convert booleans to 0/1 for Zabbix compatibility.
        "123" -> 123
        "-7" -> -7
        "12.34" -> 12.34
        True -> 1
        False -> 0
        """
        if isinstance(obj, dict):
            return {k: self._coerce_numbers(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._coerce_numbers(v) for v in obj]
        if isinstance(obj, bool):
            # Must check bool before str since bool is a subclass of int in Python
            return 1 if obj else 0
        if isinstance(obj, str):
            s = obj.strip()
            if self._int_re.match(s):
                try:
                    return int(s)
                except ValueError:
                    return obj
            if self._float_re.match(s):
                try:
                    return float(s)
                except ValueError:
                    return obj
            return obj
        return obj


    def fetch_all(self, request: OLTRequest) -> Any:
        stdin_script = self._stdin_script()
        self.debug.emit(f"olt: stdin_script={stdin_script!r}")
        raw = self._run_sshpass(request.host, request.password, stdin_script)
        json_text = self.output.to_json_text(raw)
        data = json.loads(json_text)
        return self._coerce_numbers(data)

    def _stdin_script(self) -> str:
        return "info\nshow all\nexit\n"

    def _run_sshpass(self, host: str, password: str, stdin_script: str) -> str:
        redacted = self._redact_password(password)
        cmd = [
            "sshpass", "-p", password,
            "ssh",
            "-o", "PreferredAuthentications=password",
            "-o", "PubkeyAuthentication=no",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
            "-T",
            f"admin@{host}",
        ]
        cmd_for_log = self._redact_cmd(cmd, password)
        self.debug.emit(f"olt: cmd={' '.join(self._shell_quote(x) for x in cmd_for_log)}")

        try:
            completed = subprocess.run(
                cmd,
                input=stdin_script,
                text=True,
                capture_output=True,
                timeout=30
            )
        except subprocess.TimeoutExpired:
            raise ValueError(f"SSH connection to {host} timed out after 30 seconds")
        except Exception as e:
            raise ValueError(f"SSH command failed: {e}")

        combined = (completed.stdout or "") + (completed.stderr or "")

        # Check for common SSH/sshpass errors
        if completed.returncode != 0:
            error_hints = []
            if "Permission denied" in combined or "Authentication failed" in combined:
                error_hints.append(f"authentication failed (check password for admin@{host})")
            if "Connection refused" in combined:
                error_hints.append(f"connection refused by {host} (SSH not running or port blocked?)")
            if "No route to host" in combined or "Host is unreachable" in combined:
                error_hints.append(f"cannot reach {host} (check IP address and network connectivity)")
            if "Connection timed out" in combined:
                error_hints.append(f"connection to {host} timed out (firewall blocking?)")
            if "Host key verification failed" in combined:
                error_hints.append(f"host key verification failed for {host}")

            if error_hints:
                raise ValueError(f"SSH error: {'; '.join(error_hints)}")

            # Generic error with some output preview
            preview = combined[:200] if combined else "(no output)"
            raise ValueError(f"SSH failed with return code {completed.returncode}: {preview}")

        self.debug.emit(f"olt: fetched bytes={len(combined)} returncode={completed.returncode}")

        if not combined.strip():
            raise ValueError(f"SSH to {host} succeeded but returned no output (OLT may not support 'cli -c \"show stat\" -j')")

        return combined

    def _redact_password(self, password: str) -> str:
        if not password:
            return "<empty>"
        if len(password) <= 2:
            return "*" * len(password)
        return password[0] + "*" * (len(password) - 2) + password[-1:]

    def _redact_cmd(self, cmd: Sequence[str], password: str) -> List[str]:
        redacted = self._redact_password(password)
        out: List[str] = []
        i = 0
        while i < len(cmd):
            if cmd[i] == "-p" and i + 1 < len(cmd):
                out.extend([cmd[i], redacted])
                i += 2
            else:
                out.append(cmd[i])
                i += 1
        return out


    def _shell_quote(self, s: str) -> str:
        if re.fullmatch(r"[A-Za-z0-9_./:@=-]+", s):
            return s
        return "'" + s.replace("'", "'\"'\"'") + "'"


class CacheStore:
    def __init__(self, debug: DebugLog):
        self.debug = debug

    def load_if_fresh(self, policy: CachePolicy) -> Optional[Any]:
        self.debug.emit(f"cache: enabled={policy.enabled} path={policy.path} ttl={policy.ttl_seconds}s")
        if not policy.enabled:
            self.debug.emit("cache: disabled (--no-cache)")
            return None
        if not os.path.isfile(policy.path):
            self.debug.emit("cache: miss (no file)")
            return None
        age = time.time() - os.path.getmtime(policy.path)
        if age > policy.ttl_seconds:
            self.debug.emit(f"cache: stale age={age:.1f}s > ttl")
            return None
        with open(policy.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.debug.emit(f"cache: hit age={age:.1f}s")
        return data

    def save(self, policy: CachePolicy, data: Any) -> None:
        if not policy.enabled:
            return
        directory = os.path.dirname(policy.path) or "."

        try:
            os.makedirs(directory, exist_ok=True)
        except OSError as e:
            self.debug.emit(f"cache: failed to create directory {directory}: {e}")
            raise ValueError(f"Cannot create cache directory {directory}: {e}. Check permissions.")

        # Check if directory is writable
        if not os.access(directory, os.W_OK):
            import pwd
            try:
                current_user = pwd.getpwuid(os.getuid()).pw_name
            except Exception:
                current_user = f"uid={os.getuid()}"
            raise ValueError(
                f"Cache directory {directory} is not writable by user {current_user}. "
                f"Run: sudo chown -R zabbix:zabbix {directory}"
            )

        tmp_path = policy.path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, policy.path)
            self.debug.emit(f"cache: wrote {policy.path}")
        except OSError as e:
            self.debug.emit(f"cache: failed to write {policy.path}: {e}")
            raise ValueError(f"Cannot write cache file {policy.path}: {e}. Check permissions.")
        except Exception as e:
            self.debug.emit(f"cache: unexpected error writing {policy.path}: {e}")
            # Clean up temp file if it exists
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            raise ValueError(f"Failed to save cache: {e}")


@dataclass(frozen=True)
class PathToken:
    kind: str
    value: Union[str, int, None] = None
    filter_field: Optional[str] = None
    filter_value: Optional[str] = None


class JsonPath:
    token_re = re.compile(
        r"""
        (?:
            \.?
            (?P<key>[A-Za-z_][A-Za-z0-9_-]*)
        )
        |
        (?:
            \.?
            "(?P<qkey>[^"]+)"
        )
        |
        (?:
            \[\?(?P<filter_field>[A-Za-z_][A-Za-z0-9_]*)=(?P<filter_value>[^\]]+)\]
        )
        |
        (?:
            \[(?P<index>\d+|\*)\]
        )
        |
        (?:
            \[(?P<bqkey>"[^"]+"|'[^']+')\]
        )
        """,
        re.VERBOSE,
    )

    def parse(self, path: str) -> List[PathToken]:
        tokens: List[PathToken] = []
        pos = 0
        for m in self.token_re.finditer(path):
            if m.start() != pos:
                raise ValueError(f"invalid path near: {path[pos:]}")
            pos = m.end()
            if m.group("key"):
                tokens.append(PathToken("key", m.group("key")))
            elif m.group("qkey"):
                tokens.append(PathToken("key", m.group("qkey")))
            elif m.group("filter_field"):
                tokens.append(PathToken(
                    "filter",
                    None,
                    filter_field=m.group("filter_field"),
                    filter_value=m.group("filter_value")
                ))
            elif m.group("filter_field"):
                tokens.append(PathToken(
                    "filter",
                    None,
                    filter_field=m.group("filter_field"),
                    filter_value=m.group("filter_value")
                ))
            elif m.group("index"):
                idx = m.group("index")
                tokens.append(PathToken("wildcard" if idx == "*" else "index", None if idx == "*" else int(idx)))
            elif m.group("bqkey"):
                s = m.group("bqkey")
                tokens.append(PathToken("key", s[1:-1]))
        if pos != len(path):
            raise ValueError(f"invalid path near: {path[pos:]}")
        return tokens

    def select(self, data: Any, path: Optional[str]) -> Any:
        if not path:
            return data
        tokens = self.parse(path)
        return self._apply_tokens(data, tokens)

    def _apply_tokens(self, data: Any, tokens: List[PathToken]) -> Any:
        current = data
        for i, token in enumerate(tokens):
            if token.kind == "wildcard":
                # Apply wildcard and any remaining tokens to each array element
                remaining_tokens = tokens[i + 1:]
                return self._apply_wildcard(current, remaining_tokens)
            current = self._apply_one(current, token)
        return current

    def _apply_wildcard(self, current: Any, remaining_tokens: List[PathToken]) -> Any:
        """Apply wildcard and any remaining tokens to each element in an array."""
        if not isinstance(current, list):
            return None  # Return None for invalid wildcard instead of error

        if not remaining_tokens:
            # No more tokens, just return the array
            return current[:]

        # Apply remaining tokens to each element
        results = []
        for item in current:
            result = self._apply_tokens(item, remaining_tokens)
            results.append(result)
        return results

    def _apply_one(self, current: Any, token: PathToken) -> Any:
        if token.kind == "key":
            if not isinstance(current, dict):
                return None  # Return None for missing data instead of error
            key = str(token.value)
            if key not in current:
                return None  # Return None for missing keys instead of error
            return current[key]
        if token.kind == "filter":
            if not isinstance(current, list):
                return None  # Return None for invalid filter instead of error
            # Filter array by field=value
            field = token.filter_field
            value = token.filter_value
            for item in current:
                if isinstance(item, dict) and field in item:
                    # Convert both to strings for comparison
                    if str(item[field]) == value:
                        return item
            return None  # Return None when no item found instead of error
        if token.kind == "index":
            if not isinstance(current, list):
                return None  # Return None for invalid index instead of error
            idx = int(token.value)
            if idx < 0 or idx >= len(current):
                return None  # Return None for out of range instead of error
            return current[idx]
        # Note: wildcard is now handled in _apply_tokens, not here
        raise ValueError(f"unknown token kind {token.kind}")

    def _closest_key_hint(self, requested: str, available: Iterable[str]) -> str:
        matches = difflib.get_close_matches(requested, list(available), n=1, cutoff=0.6)
        return f" is '{matches[0]}' what you're looking for?" if matches else ""


class OLTClient:
    # Array sort configuration: maps array path to sort field
    # This matches ARRAY_SELECTORS from the template builder
    ARRAY_SORT_FIELDS = {
        ("ONU",): "SN",
        ("PON",): "Name",
        ("Ethernet",): "Name",
        ("System", "Fans"): "Name",
        ("System", "ThermalStatus"): "Name",
    }

    # Lock configuration
    OLT_LOCK_TIMEOUT = int(os.environ.get("OLT_LOCK_TIMEOUT", 30))
    OLT_LOCK_POLL_INTERVAL = 0.25  # 250ms

    def __init__(self, transport: OLTTransport, cache: CacheStore, debug: DebugLog):
        self.transport = transport
        self.cache = cache
        self.debug = debug

    def _sort_object_keys(self, obj: Any, priority_key: Optional[str] = None) -> Any:
        """Sort keys within a dict, putting priority_key first if specified."""
        if isinstance(obj, dict):
            # If priority key specified, sort with it first, then rest alphabetically
            if priority_key and priority_key in obj:
                sorted_keys = [priority_key] + sorted([k for k in obj.keys() if k != priority_key])
                return {k: obj[k] for k in sorted_keys}
            else:
                # Just sort alphabetically
                return {k: obj[k] for k in sorted(obj.keys())}
        elif isinstance(obj, list):
            return [self._sort_object_keys(item, priority_key) for item in obj]
        else:
            return obj

    def _sort_arrays(self, data: Any) -> Any:
        """Sort arrays by their selector fields and reorder keys within objects to optimize filter searches."""
        if not isinstance(data, dict):
            return data

        # Sort top-level arrays and reorder keys within each item
        for (array_name,), sort_field in [(k, v) for k, v in self.ARRAY_SORT_FIELDS.items() if len(k) == 1]:
            if array_name in data and isinstance(data[array_name], list):
                # Sort array items by the field value
                data[array_name] = sorted(
                    data[array_name],
                    key=lambda item: str(item.get(sort_field, "")) if isinstance(item, dict) else ""
                )
                # Reorder keys within each item to put sort_field first
                data[array_name] = [
                    self._sort_object_keys(item, priority_key=sort_field)
                    for item in data[array_name]
                ]

        # Sort nested arrays (e.g., System.Fans)
        for (parent, child), sort_field in [(k, v) for k, v in self.ARRAY_SORT_FIELDS.items() if len(k) == 2]:
            if parent in data and isinstance(data[parent], dict):
                if child in data[parent] and isinstance(data[parent][child], list):
                    # Sort array items by the field value
                    data[parent][child] = sorted(
                        data[parent][child],
                        key=lambda item: str(item.get(sort_field, "")) if isinstance(item, dict) else ""
                    )
                    # Reorder keys within each item to put sort_field first
                    data[parent][child] = [
                        self._sort_object_keys(item, priority_key=sort_field)
                        for item in data[parent][child]
                    ]

        return data

    def get_all(self, request: OLTRequest, policy: CachePolicy) -> Any:
        lock_manager = LockManager(policy.host, self.debug)

        # Check if cache is fresh
        cached = self.cache.load_if_fresh(policy)
        if cached is not None:
            return cached

        # Cache is stale or disabled, need to fetch
        if lock_manager.acquire():
            try:
                # We acquired the lock, fetch and cache
                data = self.transport.fetch_all(request)
                # Sort arrays before caching to optimize filter searches
                data = self._sort_arrays(data)
                self.cache.save(policy, data)
                return data
            finally:
                lock_manager.release()
        else:
            # Failed to acquire lock, wait for refresh
            if lock_manager.wait_for_refresh(policy):
                # Cache became fresh while waiting
                cached = self.cache.load_if_fresh(policy)
                if cached is not None:
                    return cached
            # Timeout or other issue, proceed with fetch anyway (no lock)
            self.debug.emit("lock: proceeding without lock after timeout")
            data = self.transport.fetch_all(request)
            # Sort arrays
            data = self._sort_arrays(data)
            # Don't save cache since we don't have lock
            return data


class LockManager:
    def __init__(self, host: str, debug: DebugLog):
        self.host = host
        self.debug = debug

    def _sanitize_host(self, host: str) -> str:
        h = (host or "").strip()
        if not h:
            return "unknown"

        if h.startswith(("http://", "https://")):
            from urllib.parse import urlparse
            p = urlparse(h)
            h = p.netloc or p.path

        h = h.split("/", 1)[0]

        if h.startswith("[") and "]" in h:
            h = h[1:h.index("]")]

        if ":" in h and h.count(":") == 1 and "[" not in h and "]" not in h:
            h = h.split(":", 1)[0]

        h = h.replace(":", "-")

        safe_chars = []
        for ch in h:
            if ch.isalnum() or ch in "._-":
                safe_chars.append(ch)
            else:
                safe_chars.append("_")

        h = "".join(safe_chars).strip("._-")
        return h or "unknown"

    def _lock_path(self) -> str:
        cache_dir = os.path.dirname(self._cache_path())
        safe_host = self._sanitize_host(self.host)
        return os.path.join(cache_dir, f"{safe_host}.lock")

    def _cache_path(self) -> str:
        # This is similar to OLTCLI._default_cache_path but we need to replicate logic
        name = self._sanitize_host(self.host)
        filename = f"{name}.stats.json"

        base = os.environ.get("OLT_CACHE_DIR")
        if base and os.path.isdir(base) and os.access(base, os.W_OK):
            return os.path.join(base, filename)

        if os.path.isdir("/var/cache/cambium-olt") and os.access("/var/cache/cambium-olt", os.W_OK):
            return os.path.join("/var/cache/cambium-olt", filename)

        if os.path.isdir("/tmp") and os.access("/tmp", os.W_OK):
            return os.path.join("/tmp", filename)

        base = tempfile.gettempdir()
        return os.path.join(base, filename)

    def acquire(self) -> bool:
        lock_path = self._lock_path()
        try:
            os.makedirs(os.path.dirname(lock_path), exist_ok=True)
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            self.debug.emit(f"lock: acquired {lock_path}")
            return True
        except FileExistsError:
            self.debug.emit(f"lock: already exists {lock_path}")
            return False
        except OSError as e:
            self.debug.emit(f"lock: failed to acquire {lock_path}: {e}")
            return False

    def release(self) -> None:
        lock_path = self._lock_path()
        try:
            os.remove(lock_path)
            self.debug.emit(f"lock: released {lock_path}")
        except FileNotFoundError:
            self.debug.emit(f"lock: already released {lock_path}")
        except OSError as e:
            self.debug.emit(f"lock: failed to release {lock_path}: {e}")

    def wait_for_refresh(self, policy: CachePolicy) -> bool:
        lock_path = self._lock_path()
        timeout = OLTClient.OLT_LOCK_TIMEOUT
        poll_interval = OLTClient.OLT_LOCK_POLL_INTERVAL
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if cache is now fresh
            if self._is_cache_fresh(policy):
                self.debug.emit("lock: cache became fresh while waiting")
                return True
            # Check if lock is stale (>10s old)
            if os.path.exists(lock_path):
                lock_age = time.time() - os.path.getmtime(lock_path)
                if lock_age > 10:
                    self.debug.emit(f"lock: stale lock detected (age={lock_age:.1f}s), touching and proceeding")
                    try:
                        os.utime(lock_path, None)  # Touch the file
                        return True  # Proceed with fetch
                    except OSError as e:
                        self.debug.emit(f"lock: failed to touch stale lock: {e}")
            time.sleep(poll_interval)
        self.debug.emit(f"lock: timeout after {timeout}s")
        return False

    def _is_cache_fresh(self, policy: CachePolicy) -> bool:
        if not policy.enabled:
            return False
        if not os.path.isfile(policy.path):
            return False
        age = time.time() - os.path.getmtime(policy.path)
        return age <= policy.ttl_seconds


class PathProjector:
    def __init__(self, selector: JsonPath, debug: DebugLog):
        self.selector = selector
        self.debug = debug

    def project(self, data: Any, paths: Sequence[str]) -> Any:
        if not paths:
            self.debug.emit("path: <none> -> full json")
            return data
        if len(paths) == 1:
            selection = self.selector.select(data, paths[0])
            self.debug.emit(f"path: {paths[0]} -> {self._shape(selection)}")
            return selection
        projected = {p: self.selector.select(data, p) for p in paths}
        self.debug.emit(f"path: {len(paths)} paths -> object")
        return projected

    def _shape(self, value: Any) -> str:
        if isinstance(value, dict):
            return "object"
        if isinstance(value, list):
            return "array"
        return "scalar"


class OLTCLI:
    def __init__(self):
        self.parser = self._build_parser()

    def run(self, argv: Sequence[str]) -> int:
        args = self.parser.parse_args(argv)
        if args.cache_file is None:
            args.cache_file = self._default_cache_path(args.host)

        # If --cat-cache is set, just output the cache file and exit
        if args.cat_cache:
            try:
                with open(args.cache_file, 'r') as f:
                    sys.stdout.write(f.read())
                return 0
            except FileNotFoundError:
                sys.stderr.write(f"error: cache file not found: {args.cache_file}\n")
                return 2
            except Exception as e:
                sys.stderr.write(f"error: {e}\n")
                return 2

        debug = DebugLog(args.debug)
        request = OLTRequest(args.host, args.password)
        policy = CachePolicy(args.cache_file, args.cache_ttl, not args.no_cache, args.host)
        client = OLTClient(OLTTransport(OLTOutput(debug), debug), CacheStore(debug), debug)
        projector = PathProjector(JsonPath(), debug)
        try:
            data = client.get_all(request, policy)
            selection = projector.project(data, args.paths)
        except Exception as e:
            self._emit_error(str(e))
            return 1
        self._emit_value(selection)
        return 0

    def _build_parser(self) -> argparse.ArgumentParser:
        class FriendlyParser(argparse.ArgumentParser):
            def error(self, message):
                self.print_help(sys.stderr)
                self.exit(2, f"\nerror: {message}\n")


        p = FriendlyParser(
            prog="olt_get.py",
            description="Fetch full OLT JSON, cache it, optionally project one or more JSON paths.",
            formatter_class=argparse.RawTextHelpFormatter,
            epilog=(
                "Examples:\n"
                "  cambium_olt_ssh_json.py 192.168.50.10 password\n"
                "  cambium_olt_ssh_json.py 192.168.50.10 password 'Ethernet'\n"
                "  cambium_olt_ssh_json.py 192.168.50.10 password 'Ethernet[0].Status' 'Ethernet[0].Speed'\n"
                "  cambium_olt_ssh_json.py 192.168.50.10 password --no-cache 'Ethernet[0].RxMulticastPackets'\n"
                "  cambium_olt_ssh_json.py 192.168.50.10 password --debug 'Ethernet[0].TxBytes'\n"
                "  cambium_olt_ssh_json.py 192.168.50.10 password 'System.PowerStatus.\"Left slot\".Power'\n"
            )
        )
        p.add_argument("host", help="OLT management IP/hostname")
        p.add_argument("password", help="Password for admin@<host> SSH login")
        p.add_argument("paths", nargs="*", help="Optional JSON path(s). It's best to wrap each path in single quotes.")
        p.add_argument("--cache-file", default=None, help="Cache file path")
        p.add_argument("--cache-ttl", type=int, default=60, help="Cache TTL seconds")
        p.add_argument("--no-cache", action="store_true", help="Disable cache read/write")
        p.add_argument("--cat-cache", action="store_true", help="Just output cache file (bypasses 64KB Zabbix external script limit)")
        p.add_argument("--debug", action="store_true", help="Print debug info to stderr")
        return p

    @staticmethod
    def _sanatize_host(host: str) -> str:
        h = (host or "").strip()
        if not h:
            return "unknown"

        if h.startswith(("http://", "https://")):
            p = urlparse(h)
            h = p.netloc or p.path

        h = h.split("/", 1)[0]

        if h.startswith("[") and "]" in h:
            h = h[1:h.index("]")]

        if ":" in h and h.count(":") == 1 and "[" not in h and "]" not in h:
            h = h.split(":", 1)[0]

        h = h.replace(":", "-")

        safe_chars = []
        for ch in h:
            if ch.isalnum() or ch in "._-":
                safe_chars.append(ch)
            else:
                safe_chars.append("_")

        h = "".join(safe_chars).strip("._-")
        return h or "unknown"

    def _default_cache_path(self, host: str) -> str:
        name = self._sanatize_host(host)
        filename = f"{name}.stats.json"

        base = os.environ.get("OLT_CACHE_DIR")
        if base and os.path.isdir(base) and os.access(base, os.W_OK):
            return os.path.join(base, filename)

        if os.path.isdir("/var/cache/cambium-olt") and os.access("/var/cache/cambium-olt", os.W_OK):
            return os.path.join("/var/cache/cambium-olt", filename)

        if os.path.isdir("/tmp") and os.access("/tmp", os.W_OK):
            return os.path.join("/tmp", filename)

        base = tempfile.gettempdir()
        return os.path.join(base, filename)


    def _emit_value(self, value: Any) -> None:
        if self._is_scalar(value):
            if value is None:
                sys.stdout.write("0\n")  # Return 0 for missing data
                return
            # Check if value is an error message and convert to 0
            if isinstance(value, str) and value.startswith("error:"):
                sys.stdout.write("0\n")  # Return 0 for error messages
                return
            # Convert -1 to 0 for Zabbix unsigned compatibility (sentinel values)
            if isinstance(value, (int, float)) and value == -1:
                sys.stdout.write("0\n")  # Return 0 for -1 sentinel values
                return
            sys.stdout.write("" if value is None else str(value))
            if value is not None:
                sys.stdout.write("\n")
            return
        print(json.dumps(value, indent=2))

    def _emit_error(self, message: str) -> None:
        sys.stderr.write(f"error: {message}\n")

    def _emit_key_error(self, err: KeyError) -> None:
        msg = err.args[0] if err.args else str(err)
        sys.stderr.write("error: " + msg.replace(". available:", ".\navailable:") + "\n")


    def _is_scalar(self, value: Any) -> bool:
        return isinstance(value, (str, int, float, bool)) or value is None


class Program:
    def main(self, argv: Sequence[str]) -> int:
        return OLTCLI().run(argv)


if __name__ == "__main__":
    raise SystemExit(Program().main(sys.argv[1:]))
