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

def _generate_dummy_pdf_content():
    """Generates a byte string of a minimal, valid PDF."""
    # A simple, one-page blank PDF.
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

def _create_test_email(recipient, subject, pdf_filename):
    """
    Creates a multipart email object mimicking the real scanner email.
    """
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient
    msg['Subject'] = subject
    msg['X-Mailer'] = 'Jules Test-Mode Client'

    # Attach the plain text part
    msg.attach(MIMEText("Image data has been attached.", 'plain'))

    # Attach the PDF part
    pdf_content = _generate_dummy_pdf_content()
    part = MIMEBase("application", "pdf")
    part.set_payload(pdf_content)
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename=\"{pdf_filename}\"",
    )
    msg.attach(part)

    return msg.as_string()

# --- Main Test Mode Runner ---

async def run_test_mailer():
    """
    The main async function for test mode. Runs an infinite loop to send emails.
    """
    logger.info("Test mode enabled. Starting automatic email sender...")
    await asyncio.sleep(2) # Give the SMTP server a moment to start up

    counter = 1
    name_cycler = itertools.cycle(RECIPIENT_NAMES)

    while True:
        try:
            # 1. Get the next recipient from the cycle
            full_name = next(name_cycler)
            first_initial = full_name[0].lower()
            last_name = full_name.split(' ')[1].lower()
            username = f"{first_initial}{last_name}"
            recipient_email = f"{username}@{DOMAIN}"

            # 2. Prepare email details
            pdf_filename = f"test_{counter}.pdf"
            subject = f"Scanned from Test-Mode"

            # 3. Create and send the email
            email_body = _create_test_email(recipient_email, subject, pdf_filename)
            with smtplib.SMTP("localhost", 1025) as server:
                server.sendmail(SENDER_EMAIL, [recipient_email], email_body)

            logger.debug(f"TEST SENDER: Sent {pdf_filename} to {recipient_email}")

            # 4. Increment counter and wait for the next cycle
            counter += 1
            await asyncio.sleep(SEND_INTERVAL_SECONDS)

        except ConnectionRefusedError:
            logger.error("TEST SENDER: Connection refused. Is the SMTP server running? Retrying in 15s...")
            await asyncio.sleep(SEND_INTERVAL_SECONDS)
        except Exception as e:
            logger.error(f"TEST SENDER: An unexpected error occurred: {e}")
            await asyncio.sleep(SEND_INTERVAL_SECONDS)
