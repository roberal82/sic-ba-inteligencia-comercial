"""Configuracion de logging estructurado con loguru. Nunca registra secretos."""
import sys

from loguru import logger

_REDACT_KEYS = ("api_key", "token", "password", "secret", "authorization")


def _redact(record: dict) -> bool:
    message = record["message"].lower()
    if any(key in message for key in _REDACT_KEYS) and "=" in message:
        record["message"] = "[mensaje con posible dato sensible omitido de logs]"
    return True


def configure_logging(level: str = "INFO") -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=level,
        filter=_redact,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
            "<cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
        ),
        backtrace=False,
        diagnose=False,
    )


__all__ = ["logger", "configure_logging"]
