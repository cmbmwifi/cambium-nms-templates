FROM python:3.11-slim

# Install SSH dependencies
RUN apt-get update && \
    apt-get install -y \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir asyncssh

# Create directory structure
WORKDIR /app

# Copy mock server and fixtures
COPY mock_olt_ssh_server.py /app/
COPY olt-sample-output.json /app/fixtures/olt-sample-output.json

# Make script executable
RUN chmod +x /app/mock_olt_ssh_server.py

# Expose SSH port
EXPOSE 22

# Run the mock SSH server
CMD ["python3", "/app/mock_olt_ssh_server.py", "--host", "0.0.0.0", "--port", "22", "--fixture", "/app/fixtures/olt-sample-output.json", "--password", "password"]
