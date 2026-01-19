FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install basic dependencies and Python
RUN apt-get update && \
    apt-get install -y \
    bash \
    whiptail \
    grep \
    sed \
    coreutils \
    python3 \
    python3-pip \
    python3-venv \
    sshpass \
    openssh-client \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python testing packages
RUN pip3 install --no-cache-dir pexpect pyyaml

# Create working directory
WORKDIR /root

# Copy installer and template files
# These will be mounted at runtime

CMD ["/bin/bash"]
