import logging
from threading import Event

from api.settings import get_settings

logger = logging.getLogger(__name__)


def run() -> None:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO)
    logger.info(
        "Trackline worker environment ready (%s); job processing is not implemented",
        settings.environment,
    )

    try:
        Event().wait()
    except KeyboardInterrupt:
        logger.info("Trackline worker stopped")


if __name__ == "__main__":
    run()
