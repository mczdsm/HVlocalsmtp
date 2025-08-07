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
            os.makedirs(folder_path, exist_ok=True)
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

                file_path = os.path.join(folder_path, filename)

                try:
                    with open(file_path, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    logger.info(f"Saved PDF scan '{filename}' to user folder '{local_part}'")
                    attachment_count += 1
                except Exception as e:
                    logger.error(f"Failed to save attachment {filename} to {file_path}: {e}")
            else:
                logger.debug(f"Skipping non-PDF attachment with content type: {part.get_content_type()}")

        if attachment_count == 0:
            logger.debug("No PDF attachments found in the email.")

        return '250 OK'

async def main():
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
