import asyncio
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import Envelope, Session
import email
import os
from email import policy
from email.parser import BytesParser
from logger_config import logger

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
        
        # Create folder if it doesn't exist
        base_path = '/scans/users/'
        folder_path = os.path.join(base_path, local_part)
        try:
            os.makedirs(folder_path, exist_ok=True)
            # Set folder permissions to allow Samba access but prevent folder deletion
            # 755 = owner rwx, group/others rx (can't delete folder)
            os.chmod(folder_path, 0o777)
            # Set ownership to match Samba user (1001:1001)
            os.chown(folder_path, 1001, 1001)
            logger.debug(f"Ensured directory exists: {folder_path}")
        except OSError as e:
            logger.error(f"Could not create directory {folder_path}: {e}")
            return '500 Internal server error'
        
        # Extract and save attachments
        attachment_count = 0
        for part in msg.iter_attachments():
            if part.get_content_type() == 'application/pdf':
                filename = part.get_filename()
                if not filename:
                    filename = 'scan.pdf'
                    logger.debug("Attachment has no filename, defaulting to 'scan.pdf'")

                original_filepath = os.path.join(folder_path, filename)
                final_filepath = _find_unique_filepath(original_filepath)

                if original_filepath != final_filepath:
                    final_filename = os.path.basename(final_filepath)
                    logger.info(f"File '{filename}' already exists. Saving as '{final_filename}' instead.")
                    filename = final_filename

                try:
                    with open(final_filepath, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    # Set file permissions and ownership for Samba compatibility
                    # 666 = owner/group/others can read/write
                    os.chmod(final_filepath, 0o666)
                    # Set ownership to match Samba user (1001:1001)
                    os.chown(final_filepath, 1001, 1001)
                    logger.info(f"Saved PDF scan '{filename}' to user folder '{local_part}'")
                    attachment_count += 1
                except Exception as e:
                    logger.error(f"Failed to save attachment {filename} to {final_filepath}: {e}")
            else:
                logger.debug(f"Skipping non-PDF attachment with content type: {part.get_content_type()}")

        if attachment_count == 0:
            logger.debug("No PDF attachments found in the email.")

        return '250 OK'

async def main():
    # Check if Test Mode is enabled
    if os.environ.get('TEST_MODE', 'false').lower() == 'true':
        from test_sender import run_test_mailer
        # Start the test mailer as a background task
        asyncio.create_task(run_test_mailer())

    logger.info("Starting SMTP server...")
    handler = CustomHandler()
    controller = Controller(handler, hostname='0.0.0.0', port=1025)
    controller.start()
    logger.info("SMTP server is listening on port 1025.")
    await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("SMTP server shutting down.")