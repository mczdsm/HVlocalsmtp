#!/bin/bash

# This script sets up proper permissions for the user folders
# It should be run as part of container startup or as a periodic maintenance task

SCANS_DIR="/scans/users"

# Create the base users directory if it doesn't exist
mkdir -p "$SCANS_DIR"

# Find all user directories and set proper permissions
find "$SCANS_DIR" -maxdepth 1 -type d -not -path "$SCANS_DIR" | while read -r user_dir; do
    echo "Setting permissions for $user_dir"
    
    # Set directory permissions: owner can rwx, group can rx, others can rx
    # This prevents deletion of the folder itself by winuser
    # Set directory permissions: owner can rwx, group can rx, others can rx
    # This prevents deletion of the folder itself by winuser
    chmod 755 "$user_dir"

    # Set default ACLs for new files/directories created within this folder
    # This ensures that new files/dirs inherit group write permissions
    setfacl -d -m g:1001:rwx "$user_dir"
    
    # Set permissions for all files in the directory: owner and group can rw, others can r
    # This allows winuser (in group 1001) to modify/delete files
    find "$user_dir" -type f -exec chmod 664 {} \;
    
    # Ensure ownership is consistent (1001:1001 matches the Samba user)
    chown -R 1001:1001 "$user_dir"
done

echo "Permissions setup complete"