"""
Test Mode Module - Separated from production code for cleaner architecture
"""
import asyncio
import os
from logger_config import logger


async def start_test_mode():
    """
    Start test mode if enabled via environment variable.
    This function can be called from the main application.
    """
    if os.environ.get('TEST_MODE', 'false').lower() == 'true':
        from test_sender import run_test_mailer
        logger.info("Test mode enabled - starting test email sender")
        asyncio.create_task(run_test_mailer())
        return True
    return False