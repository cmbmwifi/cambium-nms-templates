#!/usr/bin/env python3
"""
Mock Cambium Fiber OLT SSH Server

Simulates a real OLT device by:
- Accepting SSH connections on port 22
- Authenticating admin user with password
- Responding to CLI commands with realistic output
- Returning JSON fixture data

Usage:
    python3 mock_olt_ssh_server.py [--fixture FIXTURE_FILE] [--port PORT]
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

try:
    import asyncssh
except ImportError:
    print("Error: asyncssh is required. Install with: pip install asyncssh", file=sys.stderr)
    sys.exit(1)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class MockOLTServer(asyncssh.SSHServer):
    """SSH server that authenticates and handles connections"""

    def __init__(self, password: str = "password", session_factory=None):
        self.password = password
        self.session_factory = session_factory

    def connection_made(self, conn: asyncssh.SSHServerConnection) -> None:
        peer = conn.get_extra_info('peername')
        logger.info(f"SSH connection from {peer[0]}:{peer[1]}")

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            logger.error(f"SSH connection error: {exc}")
        else:
            logger.info("SSH connection closed")

    def begin_auth(self, username: str) -> bool:
        # Only accept 'admin' username
        return username == 'admin'

    def password_auth_supported(self) -> bool:
        return True

    def validate_password(self, username: str, password: str) -> bool:
        """Validate password for admin user"""
        is_valid = username == 'admin' and password == self.password
        if is_valid:
            logger.info(f"Authentication successful for {username}")
        else:
            logger.warning(f"Authentication failed for {username}")
        return is_valid

    def session_requested(self) -> asyncssh.SSHServerSession:
        """Create a new session for an authenticated client"""
        logger.info("Session requested, creating MockOLTSession")
        return self.session_factory()


class MockOLTSession(asyncssh.SSHServerSession):
    """SSH session that processes commands and returns OLT data"""

    def __init__(self, fixture_data: dict):
        self.fixture_data = fixture_data
        self._buffer = ""

    def connection_made(self, chan: asyncssh.SSHServerChannel) -> None:
        self._chan = chan
        logger.info("Session connection_made called")

    def shell_requested(self) -> bool:
        logger.info("Shell requested")
        # Send initial prompt immediately when shell is requested
        self._send_prompt()
        return True

    def exec_requested(self, command: str) -> bool:
        """Handle exec requests (non-PTY commands)"""
        logger.info(f"Exec command received: {command}")
        self._process_command(command)
        self._chan.exit(0)
        return True

    def session_started(self) -> None:
        """Send initial prompt when session starts"""
        self._send_prompt()

    def data_received(self, data: str, datatype: asyncssh.DataType) -> None:
        """Handle incoming commands"""
        self._buffer += data

        # Check if we have complete commands
        if '\n' in self._buffer:
            lines = self._buffer.split('\n')
            self._buffer = lines[-1]  # Keep incomplete line in buffer

            for line in lines[:-1]:
                cmd = line.strip()
                if cmd:
                    logger.info(f"Received command: {cmd}")
                    self._process_command(cmd)

    def _process_command(self, cmd: str) -> None:
        """Process CLI commands and send responses"""
        if cmd == 'info':
            # Send info command response (usually just echoed)
            self._send_output(f"{cmd}\n")
            self._send_prompt()

        elif cmd == 'show all':
            # Send the main JSON response with realistic formatting
            self._send_olt_data()
            self._send_prompt()

        elif cmd in ('exit', 'quit', 'logout'):
            self._chan.write("Goodbye\n")
            self._chan.exit(0)

        else:
            # Unknown command
            self._send_output(f"Unknown command: {cmd}\n")
            self._send_prompt()

    def _send_olt_data(self) -> None:
        """Send OLT data with realistic CLI formatting"""
        # Add some realistic CLI noise before the JSON
        output = []
        # Don't add warning text - it breaks JSON parsing in scripts
        # output.append("Warning: Input is not a terminal (stdin is not a tty).\n")
        output.append("\x1b[0m")  # ANSI reset code

        # Add the JSON data
        json_str = json.dumps(self.fixture_data, indent=2)
        output.append(json_str)
        output.append("\n")

        self._send_output("".join(output))

    def _send_prompt(self) -> None:
        """Send CLI prompt"""
        # Realistic Cambium OLT prompt with ANSI codes
        prompt = "\x1b[0m<OLT-Mock#\x1b[0m "
        self._chan.write(prompt)

    def _send_output(self, text: str) -> None:
        """Send output to channel"""
        self._chan.write(text)

    def eof_received(self) -> bool:
        """Handle EOF from client - process any remaining buffer and close"""
        # Process any remaining commands in buffer
        if self._buffer.strip():
            cmd = self._buffer.strip()
            logger.info(f"Processing final command from buffer: {cmd}")
            self._process_command(cmd)
        # Return False to close the channel
        return False

    def break_received(self, msec: int) -> bool:
        """Handle break signal"""
        return False


async def start_server(
    host: str = '0.0.0.0',
    port: int = 22,
    fixture_path: Optional[Path] = None,
    password: str = "password"
) -> None:
    """Start the mock OLT SSH server"""

    if fixture_path is None:
        raise ValueError("fixture_path is required")

    # Load fixture data
    if not fixture_path.exists():
        logger.error(f"Fixture file not found: {fixture_path}")
        sys.exit(1)

    with open(fixture_path, 'r') as f:
        fixture_data = json.load(f)

    logger.info(f"Loaded fixture data from {fixture_path}")
    logger.info(f"Fixture contains {len(fixture_data)} top-level keys")

    # Generate or load host keys
    # For testing, we'll generate a temporary key
    host_key = asyncssh.generate_private_key('ssh-rsa')

    def session_factory(*args, **kwargs):
        return MockOLTSession(fixture_data)

    server = await asyncssh.create_server(
        lambda: MockOLTServer(password, session_factory),
        host,
        port,
        server_host_keys=[host_key],
    )

    logger.info(f"Mock OLT SSH server started on {host}:{port}")
    logger.info(f"Username: admin")
    logger.info(f"Password: {password}")
    logger.info("Waiting for connections...")

    async with server:
        await server.wait_closed()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Mock Cambium Fiber OLT SSH Server"
    )
    parser.add_argument(
        '--fixture',
        type=Path,
        default=Path(__file__).parent.parent / 'fixtures' / 'olt-sample-output.json',
        help='Path to JSON fixture file'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=22,
        help='SSH port to listen on (default: 22)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--password',
        type=str,
        default='password',
        help='Password for admin user (default: password)'
    )

    args = parser.parse_args()

    try:
        asyncio.run(start_server(
            host=args.host,
            port=args.port,
            fixture_path=args.fixture,
            password=args.password
        ))
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
