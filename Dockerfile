# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install any needed packages specified in requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

# Copy the current directory contents into the container at /app
COPY smtp_reciever.py .

# Create the directory for scans and set ownership
RUN mkdir -p /scans/users && chown appuser:appuser /scans/users

# Make port 1025 available to the world outside this container
EXPOSE 1025

# Run the application
CMD ["python", "smtp_reciever.py"]