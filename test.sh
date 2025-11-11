#!/bin/bash
set -e

# --- SCRIPT CONTEXT ---
# Get the absolute path of the script and change the current directory to it.
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"

# test.sh - Clones, sets up, and runs the SMTP PDF Receiver in test mode.
# This script is designed to be run on a clean Debian-based system.

# --- Helper Functions ---
print_info() {
    echo "INFO: $1"
}

print_error() {
    echo "ERROR: $1" >&2
    exit 1
}

# --- Main Script ---
print_info "Starting test deployment..."

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    print_error "This script must be run as root. Please use sudo."
fi

# 1. Install Dependencies
print_info "Checking and installing dependencies..."
apt-get update > /dev/null
apt-get install -y git python3 python3-pip python3-venv sudo > /dev/null
print_info "Dependencies installed."

# 2. Clone Repository if Necessary
if [ ! -d ".git" ]; then
    print_info "No git repository found. Cloning..."
    # Clone to a temporary directory
    TMP_DIR=$(mktemp -d)
    git clone https://github.com/mczdsm/HVlocalsmtp.git "$TMP_DIR"
    # Copy the contents to the current directory
    cp -a "$TMP_DIR"/. .
    rm -rf "$TMP_DIR"
else
    print_info "Git repository found. Pulling latest changes..."
    git pull
fi

# 3. Create Application User
APP_USER="smtp-receiver"
if id "$APP_USER" &>/dev/null; then
    print_info "User '$APP_USER' already exists."
else
    print_info "Creating user '$APP_USER'..."
    useradd -r -s /bin/false "$APP_USER"
fi

chown -R "$APP_USER":"$APP_USER" .

# 4. Create Directories
SCANS_PATH="/srv/scans/users"
LOG_PATH="/var/log/smtp-receiver"
print_info "Creating directories..."
mkdir -p "$SCANS_PATH"
mkdir -p "$LOG_PATH"
chown -R "$APP_USER":"$APP_USER" /srv/scans
chown -R "$APP_USER":"$APP_USER" "$LOG_PATH"
chmod -R 775 /srv/scans
chmod -R 775 "$LOG_PATH"
print_info "Directories created with correct permissions."

# 5. Set up Python Virtual Environment
print_info "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    sudo -u "$APP_USER" python3 -m venv venv
fi
sudo -u "$APP_USER" /bin/bash -c 'source venv/bin/activate; pip install -r requirements.txt'
print_info "Python virtual environment created and dependencies installed."

# 6. Configure .env file
print_info "Configuring for test mode..."
if [ ! -f .env ]; then
    cp .env.example .env
fi
sed -i 's/^TEST_MODE=.*/TEST_MODE=true/' .env
sed -i 's/^LOGGING_MODE=.*/LOGGING_MODE=DEBUG/' .env
print_info ".env file configured for testing."

# 7. Run the Application
print_info "Starting the application in test mode..."
print_info "Press Ctrl+C to stop the server."

# Run as the app user
sudo -u "$APP_USER" /bin/bash -c 'source venv/bin/activate; python smtp_receiver.py'
