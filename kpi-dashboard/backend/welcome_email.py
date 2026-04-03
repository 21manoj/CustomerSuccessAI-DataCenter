"""
Welcome Email
=============
Sends a one-time welcome email after a customer completes onboarding.

Config via environment variables:
  SMTP_HOST      — SMTP server hostname (required to send; if unset, logs and skips)
  SMTP_PORT      — port (default 587)
  SMTP_USER      — auth username
  SMTP_PASS      — auth password
  SMTP_FROM      — sender address (default noreply@cspulse.io)
  APP_BASE_URL   — public URL of the app (default https://d2oqfugrb2ltg9.cloudfront.net)
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

MCP_URL = "https://d2oqfugrb2ltg9.cloudfront.net/mcp"
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://d2oqfugrb2ltg9.cloudfront.net")


def _build_welcome_html(company_name: str, admin_email: str, login_url: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#f5f7fa;margin:0;padding:32px;">
  <div style="max-width:580px;margin:0 auto;background:#fff;border-radius:12px;
              box-shadow:0 2px 8px rgba(0,0,0,.08);overflow:hidden;">
    <!-- Header -->
    <div style="background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);padding:36px 40px;">
      <h1 style="color:#fff;margin:0;font-size:24px;font-weight:700;">
        Welcome to CS Pulse
      </h1>
      <p style="color:#c7d2fe;margin:8px 0 0;font-size:15px;">
        Your AI-powered Customer Success platform is ready.
      </p>
    </div>
    <!-- Body -->
    <div style="padding:36px 40px;">
      <p style="color:#374151;font-size:15px;line-height:1.6;margin:0 0 20px;">
        Hi <strong>{company_name}</strong> team,
      </p>
      <p style="color:#374151;font-size:15px;line-height:1.6;margin:0 0 24px;">
        Your CS Pulse account is active. Here&rsquo;s how to get started:
      </p>

      <!-- Steps -->
      <div style="background:#f9fafb;border-radius:8px;padding:24px;margin-bottom:28px;">
        <div style="margin-bottom:16px;">
          <span style="color:#4f46e5;font-weight:700;">Step 1 &mdash;</span>
          <span style="color:#374151;"> Complete the onboarding wizard to configure your KPI priorities and upload your first data.</span>
        </div>
        <div style="margin-bottom:16px;">
          <span style="color:#4f46e5;font-weight:700;">Step 2 &mdash;</span>
          <span style="color:#374151;"> Explore your dashboards: CRO, CFO, CEO, and CSM views are all pre-populated with your data.</span>
        </div>
        <div>
          <span style="color:#4f46e5;font-weight:700;">Step 3 &mdash;</span>
          <span style="color:#374151;"> Connect Claude.ai or any MCP client to your CS Pulse intelligence layer:</span>
          <div style="background:#1e293b;border-radius:6px;padding:12px 16px;margin-top:10px;
                      font-family:monospace;font-size:13px;color:#a5f3fc;word-break:break-all;">
            {MCP_URL}
          </div>
        </div>
      </div>

      <!-- CTA -->
      <div style="text-align:center;margin:28px 0;">
        <a href="{login_url}"
           style="display:inline-block;background:linear-gradient(135deg,#4f46e5,#7c3aed);
                  color:#fff;text-decoration:none;padding:14px 32px;border-radius:8px;
                  font-size:15px;font-weight:600;">
          Log In &rarr;
        </a>
      </div>

      <p style="color:#6b7280;font-size:13px;text-align:center;margin:0;">
        Logged in as <strong>{admin_email}</strong>
      </p>
    </div>
    <!-- Footer -->
    <div style="background:#f9fafb;padding:20px 40px;border-top:1px solid #e5e7eb;">
      <p style="color:#9ca3af;font-size:12px;margin:0;text-align:center;">
        CS Pulse &bull; Customer Success Intelligence Platform<br>
        Questions? Reply to this email or contact your account team.
      </p>
    </div>
  </div>
</body>
</html>"""


def _build_welcome_text(company_name: str, admin_email: str, login_url: str) -> str:
    return f"""Welcome to CS Pulse, {company_name}!

Your account is active. Here's how to get started:

1. Complete the onboarding wizard to configure your KPI priorities.
2. Explore your dashboards: CRO, CFO, CEO, and CSM views.
3. Connect Claude.ai via MCP:
   {MCP_URL}

Log in here: {login_url}
Account email: {admin_email}

— The CS Pulse Team
"""


def send_welcome_email(
    admin_email: str,
    company_name: str,
    customer_id: int,
) -> bool:
    """
    Send a welcome email to the new customer's admin.

    Returns True if sent (or skipped gracefully), False on hard error.
    Never raises — welcome email failure must not block onboarding.
    """
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    if not smtp_host:
        logger.info(
            f"[welcome_email] SMTP_HOST not configured — skipping welcome email "
            f"for customer {customer_id} ({admin_email})"
        )
        return True  # non-fatal skip

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    from_addr = os.getenv("SMTP_FROM", "noreply@cspulse.io")
    from_name = "CS Pulse"
    login_url = f"{APP_BASE_URL}/login"

    subject = f"Welcome to CS Pulse — {company_name} is ready"
    html_body = _build_welcome_html(company_name, admin_email, login_url)
    text_body = _build_welcome_text(company_name, admin_email, login_url)

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{from_name} <{from_addr}>"
    msg["To"] = admin_email
    msg["Subject"] = subject
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            if smtp_port == 587:
                server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(from_addr, [admin_email], msg.as_string())
        logger.info(
            f"[welcome_email] ✅ Sent to {admin_email} (customer {customer_id})"
        )
        return True
    except Exception as exc:
        logger.warning(
            f"[welcome_email] Failed to send to {admin_email} "
            f"(customer {customer_id}): {exc}"
        )
        return False
