FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./
COPY init-permissions.sh ./
RUN chmod +x init-permissions.sh

# Make port 1025 available to the world outside this container
EXPOSE 1025

# Run the application as root (LXC handles user mapping)
CMD ["python", "smtp_reciever.py"]