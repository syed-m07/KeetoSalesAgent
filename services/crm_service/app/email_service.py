"""
Email Service using Gmail SMTP.
Sends follow-up emails and lead alerts using a Gmail App Password.
Free: Up to 500 emails/day via Gmail SMTP.
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# Gmail SMTP config
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_email(to: str, subject: str, body: str) -> dict:
    """
    Send an email via Gmail SMTP.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body (plain text).

    Returns:
        Dict with success status and message.
    """
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")

    if not sender or not password:
        return {
            "success": False,
            "message": "Email not configured. Set EMAIL_SENDER and EMAIL_PASSWORD.",
        }

    try:
        # Build MIME message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Keeto Sales Agent <{sender}>"
        msg["To"] = to

        # Plain text part
        text_part = MIMEText(body, "plain")
        msg.attach(text_part)

        # HTML part (styled email)
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            padding: 20px; border-radius: 10px 10px 0 0;">
                    <h2 style="color: white; margin: 0;">🤖 Keeto Sales Agent</h2>
                </div>
                <div style="padding: 20px; background: #f9f9f9; border-radius: 0 0 10px 10px;
                            border: 1px solid #ddd; border-top: none;">
                    {body.replace(chr(10), '<br>')}
                </div>
                <p style="font-size: 12px; color: #999; text-align: center; margin-top: 15px;">
                    Sent by Keeto AI Sales Agent
                </p>
            </div>
        </body>
        </html>
        """
        html_part = MIMEText(html_body, "html")
        msg.attach(html_part)

        # Send via SMTP
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, to, msg.as_string())

        logger.info(f"✅ Email sent to {to}: {subject}")
        return {"success": True, "message": f"Email sent to {to}"}

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Gmail auth failed. Check EMAIL_SENDER and EMAIL_PASSWORD (App Password).")
        return {"success": False, "message": "Email authentication failed. Check credentials."}
    except Exception as e:
        logger.error(f"❌ Email send error: {e}")
        return {"success": False, "message": f"Failed to send email: {str(e)}"}


def send_lead_notification(lead_data: dict) -> dict:
    """
    Send an internal alert email about a new lead.
    Notifies the EMAIL_SENDER (you) about the new lead captured.

    Args:
        lead_data: Dict with name, email, company, summary.

    Returns:
        Dict with success/message.
    """
    sender = os.getenv("EMAIL_SENDER")
    if not sender:
        return {"success": False, "message": "EMAIL_SENDER not configured."}

    subject = f"🚀 New Lead Captured: {lead_data.get('name', 'Unknown')}"
    body = f"""New lead captured by the AI Sales Agent!

Name: {lead_data.get('name', 'N/A')}
Email: {lead_data.get('email', 'N/A')}
Phone: {lead_data.get('phone', 'N/A')}
Company: {lead_data.get('company', 'N/A')}
Summary: {lead_data.get('summary', 'N/A')}

This lead has been logged in the CRM.
"""
    return send_email(sender, subject, body)
