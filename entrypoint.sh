#!/bin/bash

# entrypoint.sh - Set up permissions and start the application

# Ensure the /scans/users directory exists and has proper permissions
mkdir -p /scans/users
chown -R 1001:1001 /scans
chmod -R 755 /scans

echo "Permissions set up complete. Starting SMTP receiver as user 1001..."

# Switch to user 1001 and start the main application
exec su -s /bin/bash -c "cd /app && python smtp_reciever.py" appuser