import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging
from typing import Dict, Optional
from email_validator import validate_email, EmailNotValidError
from app.services.notification_template import TemplateService

logger = logging.getLogger(__name__)

class EmailService:

    @staticmethod
    def send_email(to: str, subject: str, body_html: str, body_text: Optional[str] = None, from_email: Optional[str] = None, from_name: Optional[str] = None) -> Dict:
        
        from_email = from_email or getattr(settings, "NOTIFICATION_EMAIL_FROM", "noreply@marketplace.com")
        from_name = from_name or getattr(settings, "NOTIFICATION_EMAIL_FROM_NAME", "Freelancer Marketplace")
        logger.info(f"Sending email to {to} with subject: {subject}")
        
        try:
            if not EmailService._validate_email(to):
                raise ValueError(f"Invalid email address: {to}")
            
            if not subject or len(subject) == 0:
                raise ValueError("Email subject cannot be empty")
            
            if not body_html or len(body_html) == 0:
                raise ValueError("Email body cannot be empty")

            smtp_host = getattr(settings, "SMTP_HOST", None)
            smtp_port = getattr(settings, "SMTP_PORT", 587)
            smtp_user = getattr(settings, "SMTP_USER", None)
            smtp_password = getattr(settings, "SMTP_PASSWORD", None)

            if smtp_host and smtp_user and smtp_password:
                try:
                    msg = MIMEMultipart("alternative")
                    msg["Subject"] = subject
                    msg["From"] = f"{from_name} <{from_email}>"
                    msg["To"] = to

                    if body_text:
                        msg.attach(MIMEText(body_text, "plain"))
                    msg.attach(MIMEText(body_html, "html"))

                    with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
                        if getattr(settings, "SMTP_TLS", True):
                            server.starttls()
                        server.login(smtp_user, smtp_password)
                        server.send_message(msg)

                    logger.info(f"Email sent successfully to {to} via SMTP ({smtp_host})")
                    return {
                        "status": "sent",
                        "recipient": to,
                        "subject": subject,
                        "provider": "smtp"
                    }
                except Exception as e:
                    logger.error(f"Failed to send email to {to} via SMTP: {str(e)}", exc_info=True)
                    raise Exception(f"SMTP delivery failed: {str(e)}")
            else:
                # Console / Development fallback mode when no external SMTP credentials are provided
                logger.info(f"[DEV EMAIL LOG] Notification email dispatched to {to} | Subject: '{subject}'")
                return {
                    "status": "sent",
                    "recipient": to,
                    "subject": subject,
                    "provider": "dev_log"
                }

        except Exception as e:
            logger.error(f"Email delivery failed for {to}: {str(e)}")
            raise

    @staticmethod
    def _validate_email(email: str) -> bool:
        
        try:
            valid = validate_email(email, check_deliverability=False)
            return True
        except EmailNotValidError as e:
            logger.warning(f"Invalid email: {email} - {str(e)}")
            return False
    
    @staticmethod
    def send_template_email(to: str, template_name: str, context: Dict, subject: Optional[str] = None) -> Dict:
        
        logger.info(f"Sending template email '{template_name}' to {to}")
        
        try:
            template = TemplateService.get_template(template_name)
            rendered = template.render(context)
            email_subject = subject or rendered.get("subject", "Notification from Freelancer Marketplace")
            email_body = rendered.get("body", "")

            return EmailService.send_email(to=to, subject=email_subject, body_html=email_body)
        
        except Exception as e:
            logger.error(f"Failed to send template email: {str(e)}", exc_info=True)
            raise