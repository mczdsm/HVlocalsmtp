# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install any needed packages specified in requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create the top-level scans directory as ROOT. The app will create subdirectories.
RUN mkdir /scans

# Create a non-root user with a static UID/GID to match the Samba container user
RUN groupadd -g 1001 appuser && useradd -u 1001 -g 1001 appuser

# Give the new user ownership of the app and scans directories
RUN chown -R 1001:1001 /app && chown -R 1001:1001 /scans

# Switch to the non-root user for security
USER appuser

# Copy the application files. They will be owned by `appuser` because of the USER directive above.
COPY logger_config.py .
COPY smtp_reciever.py .
COPY test_sender.py .

# Make port 1025 available to the world outside this container
EXPOSE 1025

# Run the application
CMD ["python", "smtp_reciever.py"]