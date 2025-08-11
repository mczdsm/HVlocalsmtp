#!/bin/bash

# This script sets up proper permissions for the user folders
# It should be run as part of container startup or as a periodic maintenance task

SCANS_DIR="/scans/users"

# Create the base users directory if it doesn't exist
mkdir -p "$SCANS_DIR"

# Find all user directories and set proper permissions
find "$SCANS_DIR" -maxdepth 1 -type d -not -path "$SCANS_DIR" | while read -r user_dir; do
    echo "Setting permissions for $user_dir"
    
    # Set base directory permissions for the user directory: owner rwx, group rx, others rx
    # This prevents deletion of the folder itself by winuser
    chmod 755 "$user_dir"

    # Set default ACL for new files and directories created within this specific user folder
    # This ensures files created by smtp_receiver.py get correct permissions
    setfacl -d -m u::rwX,g:1001:rwX,o::rX "$user_dir"
    
    # Apply ACL to existing files in the directory: owner rw, group rw, others r
    # This ensures winuser can modify/delete existing files
    find "$user_dir" -type f -exec setfacl -m u::rw,g:1001:rw,o::r {} \;
    
    # Apply the ACL mask for files to rw
    find "$user_dir" -type f -exec setfacl -m m::rw {} \;
    
    # Ensure ownership is consistent (1001:1001 matches the Samba user)
    chown -R 1001:1001 "$user_dir"
done

echo "Permissions setup complete"