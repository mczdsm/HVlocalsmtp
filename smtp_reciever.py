import asyncio
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import Envelope, Session
import email
import os
from email import policy
from email.parser import BytesParser

class CustomHandler:
    async def handle_DATA(self, server, session: Session, envelope: Envelope):
        # Parse the email
        msg = BytesParser(policy=policy.default).parsebytes(envelope.content)
        
        # Get 'To' address and extract local part (before @)
        to_address = envelope.rcpt_tos[0].lower()  # Use first recipient
        if '@' not in to_address:
            print(f"Error: Invalid email format '{to_address}' - skipping.")
            return '550 Invalid recipient'  # Reject with SMTP error
        
        local_part = to_address.split('@')[0]  # e.g., 'john.smith' from 'john.smith@scanners.local'
        
        # Create folder if it doesn't exist
        base_path = '/scans/users/'  # Mount your SMB share here
        folder_path = os.path.join(base_path, local_part)
        os.makedirs(folder_path, exist_ok=True)
        
        # Extract and save attachments
        for part in msg.iter_attachments():
            if part.get_content_type() == 'application/pdf':
                filename = part.get_filename() or 'scan.pdf'
                file_path = os.path.join(folder_path, filename)
                with open(file_path, 'wb') as f:
                    f.write(part.get_payload(decode=True))
                print(f"Saved {filename} to {file_path}")  # Log for audits
        
        return '250 OK'  # Acknowledge receipt

async def main():
    handler = CustomHandler()
    controller = Controller(handler, hostname='0.0.0.0', port=1025)  # Listen on port 1025
    controller.start()
    await asyncio.Event().wait()  # Run forever

if __name__ == '__main__':
    asyncio.run(main())
