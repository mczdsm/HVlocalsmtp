#!/bin/bash

# This script sets up proper permissions for the user folders
# It should be run as part of container startup or as a periodic maintenance task

SCANS_DIR="/scans/users"

# Create the base users directory if it doesn't exist
mkdir -p "$SCANS_DIR"

# Find all user directories and set proper permissions
find "$SCANS_DIR" -maxdepth 1 -type d -not -path "$SCANS_DIR" | while read -r user_dir; do
    echo "Setting permissions for $user_dir"
    
    # Set directory permissions: owner and group can rwx, others can rx
    chmod 775 "$user_dir"
    
    # Set permissions for all files in the directory: owner and group can rw, others can r
    find "$user_dir" -type f -exec chmod 664 {} \;
    
    # Ensure ownership is consistent (33:33 matches the www-data user)
    chown -R 33:33 "$user_dir"
done

echo "Permissions setup complete"