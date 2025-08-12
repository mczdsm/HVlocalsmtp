import asyncio
import smtplib
import itertools
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

from logger_config import logger

# --- Configuration for Test Mode ---

RECIPIENT_NAMES = ["Bob Smith", "Jane Doe", "Peter Jones", "Mary Williams"]
DOMAIN = "scanners.local"
SENDER_EMAIL = "test-scanner@system.local"
SEND_INTERVAL_SECONDS = 15

# --- Helper Functions ---

# --- Test File Generation ---

def _generate_dummy_content(file_type):
    """Generates a byte string with the correct magic bytes for the given file type."""
    if file_type == 'pdf':
        return (
            b"%PDF-1.0\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f\n"
            b"0000000010 00000 n\n0000000059 00000 n\n"
            b"0000000103 00000 n\ntrailer<</Size 4/Root 1 0 R>>\n"
            b"startxref\n149\n%%EOF"
        )
    elif file_type == 'tif':
        # TIFF, little-endian
        return b'II*\x00\x08\x00\x00\x00' + b'A' * 20
    elif file_type == 'jpg':
        return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00' + b'A' * 20
    elif file_type == 'png':
        return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + b'A' * 20
    return b'invalid-file-content'

# --- Email Creation ---

def _create_test_email(recipient, subject, filename, file_type):
    """
    Creates a multipart email object with a test attachment of a given type.
    """
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient
    msg['Subject'] = subject
    msg['X-Mailer'] = 'Jules Test-Mode Client'

    # Attach the plain text part
    msg.attach(MIMEText("Image data has been attached.", 'plain'))

    # Determine MIME type
    mime_map = {
        'pdf': ('application', 'pdf'),
        'tif': ('image', 'tiff'),
        'jpg': ('image', 'jpeg'),
        'png': ('image', 'png')
    }
    main_type, sub_type = mime_map.get(file_type, ('application', 'octet-stream'))

    # Attach the file part
    content = _generate_dummy_content(file_type)
    part = MIMEBase(main_type, sub_type)
    part.set_payload(content)
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename=\"{filename}\"",
    )
    msg.attach(part)

    return msg.as_string()

# --- Main Test Mode Runner ---

async def run_test_mailer():
    """
    The main async function for test mode. Runs an infinite loop to send emails.
    """
    logger.info("Test mode enabled. Starting automatic email sender...")
    print("--- test_sender.py: run_test_mailer() called ---")
    await asyncio.sleep(2)  # Give the SMTP server a moment to start up

    counter = 1
    name_cycler = itertools.cycle(RECIPIENT_NAMES)
    file_type_cycler = itertools.cycle(['pdf', 'jpg', 'png', 'tif', 'txt']) # Includes an unsupported type

    while True:
        try:
            # 1. Get the next recipient and file type from the cycle
            full_name = next(name_cycler)
            file_type = next(file_type_cycler)

            first_initial = full_name[0].lower()
            last_name = full_name.split(' ')[1].lower()
            username = f"{first_initial}{last_name}"
            recipient_email = f"{username}@{DOMAIN}"

            # 2. Prepare email details
            ext_map = {'pdf': '.pdf', 'jpg': '.jpg', 'png': '.png', 'tif': '.tif', 'txt': '.txt'}
            ext = ext_map.get(file_type, '.dat')
            filename = f"test_{counter}{ext}"
            subject = f"Scanned from Test-Mode ({file_type.upper()})"

            # 3. Create and send the email
            print(f"--- test_sender.py: Sending {filename} to {recipient_email} ---")
            email_body = _create_test_email(recipient_email, subject, filename, file_type)
            with smtplib.SMTP("localhost", 1025) as server:
                server.sendmail(SENDER_EMAIL, [recipient_email], email_body)

            logger.debug(f"TEST SENDER: Sent {filename} to {recipient_email}")

            # 4. Increment counter and wait for the next cycle
            counter += 1
            # Reduced sleep time for faster testing
            await asyncio.sleep(2)

        except ConnectionRefusedError:
            logger.error("TEST SENDER: Connection refused. Is the SMTP server running? Retrying in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"TEST SENDER: An unexpected error occurred: {e}")
            await asyncio.sleep(5)
