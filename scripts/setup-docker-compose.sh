#!/bin/bash
# Install docker-compose in WSL2

set -e

echo "Installing docker-compose for WSL2..."
echo ""

# Download latest docker-compose
DOCKER_COMPOSE_VERSION="v2.24.5"
echo "Downloading docker-compose $DOCKER_COMPOSE_VERSION..."

sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose

# Make it executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
echo ""
echo "Verifying installation..."
docker-compose --version

echo ""
echo "✓ docker-compose installed successfully!"
echo ""
echo "You can now run: ./tests/integration/test-installer-execution.sh"
Automated Interactive Tests with expect
