# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install any needed packages specified in requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create the directory for scans as ROOT before we create the non-root user.
RUN mkdir -p /scans/users && \
    touch /scans/users/audit.log && \
    touch /scans/users/error.log

# Create a non-root user that will run the application
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Give the new user ownership of the application and scan directories
RUN chown -R appuser:appuser /app && chown -R appuser:appuser /scans

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