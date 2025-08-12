FROM python:3.9-slim

# Create application user with specific UID/GID for Samba compatibility
RUN groupadd -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup -d /app -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./
COPY init-permissions.sh ./
RUN chmod +x init-permissions.sh

# Create scans directory with proper ownership and make writable for volume mounting
RUN mkdir -p /scans/users && \
    chown -R appuser:appgroup /scans && \
    chmod 775 /scans && \
    chmod 775 /scans/users

# Change ownership of app directory
RUN chown -R appuser:appgroup /app

# Make port 1025 available to the world outside this container
EXPOSE 1025

# Create entrypoint script that handles permissions and runs application as root
RUN echo '#!/bin/bash' > /entrypoint.sh && \
    echo 'set -e' >> /entrypoint.sh && \
    echo '' >> /entrypoint.sh && \
    echo '# Fix permissions for mounted volume' >> /entrypoint.sh && \
    echo 'chown -R 1001:1001 /scans' >> /entrypoint.sh && \
    echo 'chmod 775 /scans' >> /entrypoint.sh && \
    echo 'mkdir -p /scans/users' >> /entrypoint.sh && \
    echo 'chown -R 1001:1001 /scans/users' >> /entrypoint.sh && \
    echo 'chmod 775 /scans/users' >> /entrypoint.sh && \
    echo '' >> /entrypoint.sh && \
    echo '# Run application as root (needed for creating directories with proper ownership)' >> /entrypoint.sh && \
    echo 'exec python smtp_reciever.py' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Run entrypoint script as root
CMD ["/entrypoint.sh"]