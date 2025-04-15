"""Email sender for notifications."""

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Dict, Any

logger = logging.getLogger("notifications.email")

class EmailSender:
    """
    Email sender for notifications.
    
    Sends email notifications using SMTP.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_email: str,
        use_tls: bool = True
    ):
        """
        Initialize the email sender.
        
        Args:
            host: SMTP host
            port: SMTP port
            username: SMTP username
            password: SMTP password
            from_email: Sender email address
            use_tls: Whether to use TLS
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls
        
        logger.info(f"Email sender initialized with host {host}:{port}")
    
    async def send(
        self,
        to_email: str,
        subject: str,
        message: str,
        html_message: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[Dict[str, bytes]] = None
    ) -> bool:
        """
        Send an email notification.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            message: Plain text message
            html_message: HTML message (optional)
            reply_to: Reply-to email address (optional)
            attachments: Dictionary of attachments {filename: data} (optional)
            
        Returns:
            True if the email was sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # Attach text part
            text_part = MIMEText(message, 'plain')
            msg.attach(text_part)
            
            # Attach HTML part if provided
            if html_message:
                html_part = MIMEText(html_message, 'html')
                msg.attach(html_part)
            
            # Attach any attachments
            if attachments:
                for filename, data in attachments.items():
                    from email.mime.application import MIMEApplication
                    attachment = MIMEApplication(data)
                    attachment['Content-Disposition'] = f'attachment; filename="{filename}"'
                    msg.attach(attachment)
            
            # Connect to SMTP server
            context = ssl.create_default_context() if self.use_tls else None
            
            if self.use_tls:
                server = smtplib.SMTP(self.host, self.port)
                server.starttls(context=context)
            else:
                server = smtplib.SMTP(self.host, self.port)
            
            # Log in
            if self.username and self.password:
                server.login(self.username, self.password)
            
            # Send the email
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False
    
    async def send_template(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        template_data: Dict[str, Any],
        reply_to: Optional[str] = None
    ) -> bool:
        """
        Send a templated email notification.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            template_name: Name of the template to use
            template_data: Data to fill the template
            reply_to: Reply-to email address (optional)
            
        Returns:
            True if the email was sent successfully, False otherwise
        """
        try:
            # In a real implementation, this would load and render a template
            # For this example, we'll use a simple approach
            
            # Prepare message
            message = f"This is a notification from the system.\n\n"
            
            # Add template data
            for key, value in template_data.items():
                if isinstance(value, dict):
                    message += f"\n{key.capitalize()}:\n"
                    for k, v in value.items():
                        message += f"  {k}: {v}\n"
                else:
                    message += f"{key}: {value}\n"
            
            # Prepare HTML message
            html_message = f"<html><body><h1>{subject}</h1><p>{message.replace('\n', '<br>')}</p></body></html>"
            
            # Send the email
            return await self.send(
                to_email=to_email,
                subject=subject,
                message=message,
                html_message=html_message,
                reply_to=reply_to
            )
            
        except Exception as e:
            logger.error(f"Error sending templated email to {to_email}: {str(e)}")
            return False 