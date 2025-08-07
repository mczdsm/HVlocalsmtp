import logging
import os
import sys

# --- Logger Configuration ---

# Get configuration from environment variables
LOGGING_MODE = os.environ.get('LOGGING_MODE', 'PRODUCTION').upper()
TEST_MODE = os.environ.get('TEST_MODE', 'false').upper()

# Create a logger
logger = logging.getLogger('smtp_receiver')
logger.setLevel(logging.DEBUG)  # Set the lowest level to capture everything

# --- Handlers and Formatters ---

# Create a custom filter to allow only INFO level messages
class InfoFilter(logging.Filter):
    def filter(self, record):
        return record.levelno == logging.INFO

# If Test Mode is on, force DEBUG logging to console for easy monitoring.
if TEST_MODE == 'TRUE' or LOGGING_MODE == 'DEBUG':
    # In DEBUG or TEST mode, log to console
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if TEST_MODE == 'TRUE':
        logger.info("Test mode is enabled. Forcing DEBUG logging to console.")
    else:
        logger.info("Logging configured for DEBUG mode.")

else: # PRODUCTION mode
    # In PRODUCTION mode, log to separate files for audit and errors

    # --- Audit Log Handler (INFO) ---
    audit_handler = logging.FileHandler('/scans/users/audit.log')
    audit_handler.setLevel(logging.INFO)
    audit_handler.addFilter(InfoFilter()) # Ensure only INFO messages are logged
    audit_formatter = logging.Formatter('%(asctime)s - %(message)s')
    audit_handler.setFormatter(audit_formatter)
    logger.addHandler(audit_handler)

    # --- Error Log Handler (ERROR) ---
    error_handler = logging.FileHandler('/scans/users/error.log')
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)

    # Also, add a console handler for errors in production, so they are visible in `docker logs`
    prod_console_handler = logging.StreamHandler(sys.stderr)
    prod_console_handler.setLevel(logging.ERROR)
    prod_console_handler.setFormatter(error_formatter)
    logger.addHandler(prod_console_handler)

    logger.info("Logging configured for PRODUCTION mode.")
