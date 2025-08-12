import logging
import os
import sys
import re

# --- Logger Configuration ---

def sanitize_log_message(message):
    """
    Sanitize log messages to prevent log injection and information disclosure.
    Removes potential sensitive information and control characters.
    """
    if not isinstance(message, str):
        message = str(message)
    
    # Remove control characters that could be used for log injection
    message = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', message)
    
    # Replace newlines and carriage returns to prevent log injection
    message = message.replace('\n', ' ').replace('\r', ' ')
    
    # Truncate very long messages to prevent log flooding
    if len(message) > 1000:
        message = message[:997] + '...'
    
    return message

class SecureFormatter(logging.Formatter):
    """Custom formatter that sanitizes log messages."""
    
    def format(self, record):
        # Sanitize the message
        if hasattr(record, 'msg') and record.msg:
            record.msg = sanitize_log_message(record.msg)
        
        # Sanitize any arguments
        if hasattr(record, 'args') and record.args:
            record.args = tuple(sanitize_log_message(str(arg)) for arg in record.args)
        
        return super().format(record)

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
    formatter = SecureFormatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if TEST_MODE == 'TRUE':
        logger.info("Test mode is enabled. Forcing DEBUG logging to console.")
    else:
        logger.info("Logging configured for DEBUG mode.")

else: # PRODUCTION mode
    # In PRODUCTION mode, log to separate files for audit and errors
    log_path = os.environ.get('LOG_PATH', '/scans/users')

    # --- Audit Log Handler (INFO) ---
    audit_handler = logging.FileHandler(f'{log_path}/audit.log')
    audit_handler.setLevel(logging.INFO)
    audit_handler.addFilter(InfoFilter()) # Ensure only INFO messages are logged
    audit_formatter = SecureFormatter('%(asctime)s - %(message)s')
    audit_handler.setFormatter(audit_formatter)
    logger.addHandler(audit_handler)

    # --- Error Log Handler (ERROR) ---
    error_handler = logging.FileHandler(f'{log_path}/error.log')
    error_handler.setLevel(logging.ERROR)
    error_formatter = SecureFormatter('%(asctime)s - %(levelname)s - %(message)s')
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)

    # Also, add a console handler for errors in production, so they are visible in `docker logs`
    prod_console_handler = logging.StreamHandler(sys.stderr)
    prod_console_handler.setLevel(logging.ERROR)
    prod_console_handler.setFormatter(error_formatter)
    logger.addHandler(prod_console_handler)

    logger.info("Logging configured for PRODUCTION mode.")
