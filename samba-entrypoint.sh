#!/bin/bash

# Run the permission initialization script
/usr/local/bin/init-permissions.sh

# Execute the original Samba entrypoint (from dperson/samba)
exec /usr/bin/samba.sh "$@"