import asyncio
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import Envelope, Session
import email
import os
from email import policy
from email.parser import BytesParser
from logger_config import logger

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
            # Explicitly set directory permissions to be group-writable
            os.makedirs(folder_path, mode=0o775, exist_ok=True)
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

                # --- Atomic file saving logic to prevent race conditions ---
                base_name, ext = os.path.splitext(filename)
                counter = 0
                while True:
                    # Determine the filename to try
                    if counter == 0:
                        current_filename = filename
                    else:
                        current_filename = f"{base_name}({counter}){ext}"

                    filepath = os.path.join(folder_path, current_filename)

                    try:
                        # 'xb' mode opens for exclusive creation, failing if the path exists.
                        with open(filepath, 'xb') as f:
                            f.write(part.get_payload(decode=True))

                        # Explicitly set file permissions to be group-writable
                        os.chmod(filepath, 0o664)

                        if counter > 0:
                            logger.info(f"File '{filename}' already exists. Saved as '{current_filename}'.")

                        logger.info(f"Saved PDF scan '{current_filename}' to user folder '{local_part}'")
                        attachment_count += 1
                        break # Exit the loop on successful save

                    except FileExistsError:
                        # This occurs if the file was created by another process after our check.
                        # Increment counter and the loop will try the next filename.
                        counter += 1
                    except Exception as e:
                        logger.error(f"Failed to save attachment {current_filename}: {e}")
                        break # Exit loop on other errors
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
