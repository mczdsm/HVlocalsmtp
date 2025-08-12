import asyncio
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import Envelope, Session
import email
import os
import re
from email import policy
from email.parser import BytesParser
from logger_config import logger

def _validate_local_part(local_part):
    """
    Validates that the local part of an email address is safe for use as a folder name.
    Only allows alphanumeric characters, dots, hyphens, and underscores.
    Prevents path traversal and other directory injection attacks.
    """
    if not local_part:
        return False
    
    if len(local_part) > 64:
        return False
    
    if local_part in ['.', '..']:
        return False
    
    if re.match(r'^[a-zA-Z0-9._-]+$', local_part):
        return True
    
    return False

def _sanitize_filename(filename):
    """
    Sanitizes a filename by removing or replacing unsafe characters.
    Prevents path traversal and ensures filesystem compatibility.
    """
    if not filename:
        return 'scan.pdf'
    
    filename = os.path.basename(filename)
    
    filename = re.sub(r'[^\w\s.-]', '_', filename)
    
    filename = filename.strip('. ')
    
    if not filename or filename in ['.', '..']:
        filename = 'scan.pdf'
    
    if not filename.lower().endswith('.pdf'):
        filename = filename + '.pdf'
    
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:251] + ext
    
    return filename

def _validate_pdf_content(content):
    """
    Basic validation to check if content appears to be a PDF file.
    Checks for PDF magic header.
    """
    if not content or len(content) < 8:
        return False
    
    return content.startswith(b'%PDF-')

def _find_unique_filepath(filepath):
    """
    Checks if a filepath exists. If it does, it appends a counter
    (e.g., (1), (2)) to the filename until a unique path is found.
    """
    if not os.path.exists(filepath):
        return filepath

    directory, filename = os.path.split(filepath)
    name, ext = os.path.splitext(filename)
    counter = 1

    while True:
        new_name = f"{name}({counter}){ext}"
        new_filepath = os.path.join(directory, new_name)
        if not os.path.exists(new_filepath):
            return new_filepath
        counter += 1

class CustomHandler:
    async def handle_DATA(self, server, session: Session, envelope: Envelope):
        logger.debug(f"Received email from: {envelope.mail_from}")
        logger.debug(f"Email intended for: {envelope.rcpt_tos}")
        
        # Parse the email
        try:
            msg = BytesParser(policy=policy.default).parsebytes(envelope.content)
        except Exception as e:
            logger.error(f"Failed to parse email: {e}")
            return '500 Could not process email'

        # Get 'To' address and extract local part (before @)
        if not envelope.rcpt_tos:
            logger.error("No recipients found in the envelope.")
            return '550 No recipient'

        to_address = envelope.rcpt_tos[0].lower()
        if '@' not in to_address:
            logger.error(f"Invalid email format '{to_address}' - rejecting.")
            return '550 Invalid recipient'
        
        local_part = to_address.split('@')[0]
        logger.debug(f"Determined local part as: {local_part}")
        
        # Validate local part to prevent path traversal
        if not _validate_local_part(local_part):
            logger.error(f"Invalid local part '{local_part}' - contains unsafe characters")
            return '550 Invalid recipient format'
        
        # Create folder if it doesn't exist
        base_path = os.environ.get('SCANS_BASE_PATH', '/scans/users/')
        folder_path = os.path.join(base_path, local_part)
        try:
            os.makedirs(folder_path, exist_ok=True)
            # Set folder permissions: owner rwx, group rwx, others rx  
            # This allows Samba user (in group 1001) to create/modify files but not delete folder
            os.chmod(folder_path, 0o775)
            # Set ownership to match Samba user configuration (1001:1001)
            os.chown(folder_path, 1001, 1001)
            logger.debug(f"Ensured directory exists: {folder_path}")
        except OSError as e:
            logger.error(f"Could not create directory {folder_path}: {e}")
            return '500 Internal server error'
        
        # Extract and save attachments
        attachment_count = 0
        max_file_size = int(os.environ.get('MAX_FILE_SIZE_MB', '50')) * 1024 * 1024  # Default 50MB
        
        for part in msg.iter_attachments():
            if part.get_content_type() == 'application/pdf':
                # Get and sanitize filename
                filename = part.get_filename()
                filename = _sanitize_filename(filename)
                
                # Get file content and validate
                try:
                    content = part.get_payload(decode=True)
                    if not content:
                        logger.debug("Empty PDF attachment, skipping")
                        continue
                        
                    # Check file size limit
                    if len(content) > max_file_size:
                        logger.warning(f"PDF attachment '{filename}' exceeds size limit ({len(content)} bytes), skipping")
                        continue
                    
                    # Validate PDF content
                    if not _validate_pdf_content(content):
                        logger.warning(f"Attachment '{filename}' does not appear to be a valid PDF, skipping")
                        continue
                        
                except Exception as e:
                    logger.error(f"Failed to process attachment {filename}: {e}")
                    continue

                original_filepath = os.path.join(folder_path, filename)
                final_filepath = _find_unique_filepath(original_filepath)

                if original_filepath != final_filepath:
                    final_filename = os.path.basename(final_filepath)
                    logger.info(f"File '{filename}' already exists. Saving as '{final_filename}' instead.")
                    filename = final_filename

                try:
                    with open(final_filepath, 'wb') as f:
                        f.write(content)
                    # Set secure file permissions: owner/group rw, others r
                    # This allows Samba user (in group 1001) to modify/delete files
                    os.chmod(final_filepath, 0o664)
                    # Set ownership to match Samba user configuration (1001:1001)
                    os.chown(final_filepath, 1001, 1001)
                    logger.info(f"Saved PDF scan '{filename}' to user folder '{local_part}' ({len(content)} bytes)")
                    attachment_count += 1
                except Exception as e:
                    logger.error(f"Failed to save attachment {filename} to {final_filepath}: {e}")
            else:
                logger.debug(f"Skipping non-PDF attachment with content type: {part.get_content_type()}")

        if attachment_count == 0:
            logger.debug("No PDF attachments found in the email.")

        return '250 OK'

async def main():
    # Start test mode if enabled
    try:
        from test_mode import start_test_mode
        await start_test_mode()
    except ImportError:
        logger.debug("Test mode module not available")

    logger.info("Starting SMTP server...")
    handler = CustomHandler()
    
    # Get server configuration from environment
    host = os.environ.get('SMTP_HOST', '0.0.0.0')
    port = int(os.environ.get('SMTP_PORT', '1025'))
    
    controller = Controller(handler, hostname=host, port=port)
    controller.start()
    logger.info(f"SMTP server is listening on {host}:{port}")
    await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("SMTP server shutting down.")