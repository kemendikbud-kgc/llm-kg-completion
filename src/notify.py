"""Desktop notifications — best-effort OS-level alerts."""

import logging

logger = logging.getLogger(__name__)


def send_notification(title: str, message: str, timeout: int = 5) -> None:
    """Send a desktop notification (best-effort, never fails).

    Args:
        title: Notification title
        message: Notification message
        timeout: Display duration in seconds
    """
    try:
        from plyer import notification

        notification.notify(title=title, message=message, timeout=timeout)
        logger.info("Notification sent: %s", title)
    except ImportError:
        logger.debug("plyer not installed, skipping notification: %s", title)
    except Exception as e:
        logger.debug("Notification failed (non-fatal): %s", e)
