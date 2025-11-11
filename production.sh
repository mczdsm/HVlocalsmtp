#!/bin/bash
set -e

# --- SCRIPT CONTEXT ---
# Get the absolute path of the script and change the current directory to it.
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"

# production.sh - Deploys and configures the SMTP PDF Receiver for production.
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
print_info "Starting production deployment..."

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    print_error "This script must be run as root. Please use sudo."
fi

# 1. Install Dependencies
print_info "Checking and installing dependencies..."
apt-get update > /dev/null
apt-get install -y git python3 python3-pip python3-venv samba sudo > /dev/null
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

# Fix incorrect filename from repository
if [ -f "smtp_reciever.py" ]; then
    print_info "Correcting filename typo: smtp_reciever.py -> smtp_receiver.py"
    mv smtp_reciever.py smtp_receiver.py
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
SCANS_PATH="/srv/scans"
USERS_PATH="/srv/scans/users"
LOG_PATH="/var/log/smtp-receiver"
print_info "Creating directories..."
mkdir -p "$USERS_PATH"
mkdir -p "$LOG_PATH"
chown -R "$APP_USER":"$APP_USER" "$SCANS_PATH"
chown -R "$APP_USER":"$APP_USER" "$LOG_PATH"
chmod -R 775 "$SCANS_PATH"
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
print_info "Configuring for production mode..."
if [ ! -f .env ]; then
    cp .env.example .env
fi
sed -i 's/^TEST_MODE=.*/TEST_MODE=false/' .env
sed -i 's/^LOGGING_MODE=.*/LOGGING_MODE=PRODUCTION/' .env
# Source the .env file to get SAMBA_USER and SAMBA_PASSWORD
set -o allexport
source .env
set +o allexport
print_info ".env file configured for production."

# 7. Configure Samba
print_info "Configuring Samba..."
if ! id "$SAMBA_USER" &>/dev/null; then
    print_info "Creating Samba user '$SAMBA_USER'..."
    useradd -r -s /bin/false "$SAMBA_USER"
fi
(echo "$SAMBA_PASSWORD"; echo "$SAMBA_PASSWORD") | smbpasswd -s -a "$SAMBA_USER"

# Create a separate config file for our share
SHARE_CONFIG_FILE="/etc/samba/conf.d/scans.conf"
mkdir -p /etc/samba/conf.d

cat <<EOF > "$SHARE_CONFIG_FILE"
[scans]
   path = /srv/scans
   browseable = yes
   read only = no
   guest ok = no
   create mask = 0664
   directory mask = 0775
   valid users = $SAMBA_USER
   force user = $APP_USER
   force group = $APP_USER
EOF

# Ensure the main smb.conf includes our custom configs
INCLUDE_DIRECTIVE="include = /etc/samba/conf.d/"
if ! grep -q "^$INCLUDE_DIRECTIVE" /etc/samba/smb.conf; then
    print_info "Adding include directive to /etc/samba/smb.conf"
    echo "$INCLUDE_DIRECTIVE" >> /etc/samba/smb.conf
fi

systemctl restart smbd
print_info "Samba configured and restarted."

# 8. Set up systemd Service
print_info "Setting up systemd service..."
cat <<EOF > /etc/systemd/system/smtp-receiver.service
[Unit]
Description=SMTP PDF Receiver Service
After=network.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python smtp_receiver.py
Restart=always
EnvironmentFile=$(pwd)/.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable smtp-receiver
systemctl start smtp-receiver
print_info "Systemd service 'smtp-receiver' created, enabled, and started."
print_info "Deployment complete. The application is running in production mode."
