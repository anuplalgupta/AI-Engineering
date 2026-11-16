"""Sending email. Locally the SMTP server is the mail viewer; nothing leaves the machine."""

import smtplib
from email.message import EmailMessage
from email.utils import format_datetime
from typing import Protocol

from ailms.platform import clock
from ailms.platform.settings import get_settings


class Mailer(Protocol):
    def send(self, to: str, subject: str, text: str) -> None: ...


class SmtpMailer:
    def __init__(self, host: str, port: int, sender: str) -> None:
        self._host, self._port, self._sender = host, port, sender

    def send(self, to: str, subject: str, text: str) -> None:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = to
        message["Subject"] = subject
        message["Date"] = format_datetime(clock.now())
        message.set_content(text)
        with smtplib.SMTP(self._host, self._port, timeout=10) as smtp:
            smtp.send_message(message)


class RecordingMailer:
    """For tests: keeps the messages instead of sending them."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    def send(self, to: str, subject: str, text: str) -> None:
        self.sent.append((to, subject, text))


_mailer: Mailer | None = None


def get_mailer() -> Mailer:
    global _mailer
    if _mailer is None:
        s = get_settings()
        _mailer = SmtpMailer(s.smtp_host, s.smtp_port, s.mail_from)
    return _mailer


def set_mailer(mailer: Mailer | None) -> None:
    global _mailer
    _mailer = mailer
