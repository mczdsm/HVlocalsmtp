# SMTP PDF Receiver & Samba Share

This project provides a simple and robust solution for receiving emails, extracting PDF attachments, and making them available via a network share. It is fully containerized using Docker and Docker Compose for easy deployment.

## Overview

The system is composed of two main services:

1.  **SMTP Receiver**: A Python-based asynchronous SMTP server that listens for incoming emails. When an email containing a PDF attachment is received, the server extracts the PDF and saves it to a user-specific folder. The folder name is determined by the local-part of the recipient's email address (e.g., `jdoe` from `jdoe@scanners.local`).
2.  **Samba Server**: A pre-configured Samba container that exposes the directory of saved scans as a network share. This allows users and other systems to easily access the processed files.

## Features

- **Automatic PDF Extraction**: Saves PDF attachments from emails into organized folders.
- **File Overwrite Prevention**: If a file with the same name already exists, a counter is appended to the new filename (e.g., `scan(1).pdf`) to prevent data loss.
- **Integrated Samba Share**: Provides immediate network access to the saved scans.
- **Configurable Logging**: Switch between `DEBUG` and `PRODUCTION` logging modes.
- **Automated Test Mode**: An included test mode automatically sends sample emails to the server, allowing for easy, hands-free validation of the entire workflow.

## Requirements

- Docker
- Docker Compose

## Configuration

The application is configured using environment variables in the `docker-compose.yml` file.

| Variable | Service | Default | Description |
|---|---|---|---|
| `LOGGING_MODE` | `smtp-receiver` | `DEBUG` | Sets the logging verbosity. **`DEBUG`**: Verbose output to the console. **`PRODUCTION`**: Separates `INFO` audit logs and `ERROR` logs into files within the share (`audit.log`, `error.log`). |
| `TEST_MODE` | `smtp-receiver` | `false` | Enables the automated test mode. **`true`**: The application will send test emails to itself every 15 seconds. |
| `USER` | `samba` | `winuser;...` | Configures the Samba user. **IMPORTANT**: You **must** replace `YourStrongPassword` with a secure password. |

## Deployment

### Standard Deployment

1.  Clone this repository.
2.  Open `docker-compose.yml` and set a secure password for the `USER` environment variable in the `samba` service.
3.  From the project root, run the following command:
    ```bash
    docker-compose up --build -d
    ```
The services will build and start in the background. The SMTP server will be listening on port `1025`, and the Samba share will be available on ports `139` and `445`.

### Testing the Service

To verify the system is working correctly, you can use the built-in test mode.

1.  In `docker-compose.yml`, set the `TEST_MODE` environment variable to `true`.
2.  Build and start the services:
    ```bash
    docker-compose up --build -d
    ```
3.  View the logs to see the test in action:
    ```bash
    docker-compose logs -f smtp-receiver
    ```
    You will see logs indicating that test emails are being sent and received, and that the PDF attachments are being saved.

## Accessing the Share

Once the Samba service is running, you can connect to the network share.

- **Host**: The IP address of the machine running Docker.
- **Share Name**: `scans`
- **Username**: `winuser`
- **Password**: The secure password you configured in `docker-compose.yml`.

Inside the share, you will find the user-specific folders containing the saved PDF files.
