"""
Email Provider Adapter
=======================
Sends emails via SMTP for playbook notifications and escalations.

Required config:
  - from_email: Sender email address
  - from_name: Sender display name

Required credentials:
  - smtp_host, smtp_port, smtp_user, smtp_password
"""

import logging
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from providers.base import ProviderBase, ProviderResult

logger = logging.getLogger(__name__)


class EmailProvider(ProviderBase):
    """Provider adapter for SMTP email."""

    PROVIDER_NAME = 'email'

    SUPPORTED_ACTIONS = {'send_alert', 'send_email', 'send_escalation'}

    def execute(
        self,
        action_name: str,
        params: Dict[str, Any],
        credentials: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> ProviderResult:
        config = config or {}
        credentials = credentials or {}
        start = time.monotonic()

        recipients = params.get('recipients', params.get('to', []))
        if isinstance(recipients, str):
            recipients = [recipients]
        if not recipients:
            return ProviderResult(
                success=False,
                provider=self.PROVIDER_NAME,
                action_name=action_name,
                error_message='No recipients specified',
            )

        subject = params.get('subject', f'CS Alert: {action_name}')
        body_html = params.get('body_html', params.get('message', ''))
        body_text = params.get('body_text', body_html)

        msg = MIMEMultipart('alternative')
        msg['From'] = f"{config.get('from_name', 'CS Pulse')} <{config.get('from_email', 'noreply@cspulse.io')}>"
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject
        msg.attach(MIMEText(body_text, 'plain'))
        if body_html:
            msg.attach(MIMEText(body_html, 'html'))

        try:
            host = credentials.get('smtp_host', 'localhost')
            port = int(credentials.get('smtp_port', 587))
            user = credentials.get('smtp_user', '')
            password = credentials.get('smtp_password', '')

            with smtplib.SMTP(host, port, timeout=15) as server:
                if port == 587:
                    server.starttls()
                if user and password:
                    server.login(user, password)
                server.sendmail(msg['From'], recipients, msg.as_string())

            duration = int((time.monotonic() - start) * 1000)
            return ProviderResult(
                success=True,
                provider=self.PROVIDER_NAME,
                action_name=action_name,
                response_data={'recipients': recipients, 'subject': subject},
                duration_ms=duration,
            )
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            return ProviderResult(
                success=False,
                provider=self.PROVIDER_NAME,
                action_name=action_name,
                error_message=str(e),
                duration_ms=duration,
            )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return bool(config.get('from_email'))
