#!/bin/bash
set -e

# --- SCRIPT CONTEXT ---
# Get the absolute path of the script and change the current directory to it.
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"

# reset.sh - Resets the environment by cleaning up all created files and users.
# This script is designed to be run on a Debian-based system.

# --- Helper Functions ---
print_info() {
    echo "INFO: $1"
}

print_error() {
    echo "ERROR: $1" >&2
    exit 1
}

# --- Main Script ---
print_info "Starting environment reset..."

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    print_error "This script must be run as root. Please use sudo."
fi

# 1. Stop and Disable systemd Service
print_info "Stopping and disabling systemd service..."
if systemctl is-active --quiet smtp-receiver; then
    systemctl stop smtp-receiver
fi
if systemctl is-enabled --quiet smtp-receiver; then
    systemctl disable smtp-receiver
fi
rm -f /etc/systemd/system/smtp-receiver.service
systemctl daemon-reload
print_info "Systemd service stopped and disabled."

# 2. Remove Directories
print_info "Removing created directories..."
rm -rf /srv/scans
rm -rf /var/log/smtp-receiver
print_info "Directories removed."

# 3. Remove Samba User and Configuration
if [ -f .env ]; then
    set -o allexport
    source .env
    set +o allexport
    if id "$SAMBA_USER" &>/dev/null; then
        print_info "Removing Samba user '$SAMBA_USER'..."
        smbpasswd -x "$SAMBA_USER"
        userdel "$SAMBA_USER"
    fi
fi
rm -f /etc/samba/conf.d/scans.conf
print_info "Samba user and configuration removed."


# 4. Remove Application User
APP_USER="smtp-receiver"
if id "$APP_USER" &>/dev/null; then
    print_info "Removing user '$APP_USER'..."
    userdel "$APP_USER"
fi

# 5. Clean Project Directory
print_info "Cleaning project directory..."
# Deletes everything except the scripts themselves and the .git directory
find . -mindepth 1 -not -name 'test.sh' -not -name 'production.sh' -not -name 'reset.sh' -not -name '.git' -exec rm -rf {} +
print_info "Project directory cleaned."

print_info "Environment reset complete."
