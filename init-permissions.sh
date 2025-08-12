#!/bin/bash

# This script sets up proper secure permissions for the user folders
# It should be run as part of container startup or as a periodic maintenance task

SCANS_DIR="/scans/users"

# Create the base users directory if it doesn't exist
mkdir -p "$SCANS_DIR"

# Find all user directories and set proper secure permissions
find "$SCANS_DIR" -maxdepth 1 -type d -not -path "$SCANS_DIR" | while read -r user_dir; do
    echo "Setting secure permissions for $user_dir"
    
    # Set directory permissions: owner/group/others rwx
    # This allows all users including Windows users to create/modify/delete files
    chmod 777 "$user_dir"
    
    # Set permissions for all files in the directory: owner/group/others rw
    # This allows all users including Windows users to modify/delete files
    find "$user_dir" -type f -exec chmod 666 {} \;
    
    # Ensure ownership is consistent (1001:1001 matches the Samba user)
    chown -R 1001:1001 "$user_dir"
done

echo "Secure permissions setup complete"