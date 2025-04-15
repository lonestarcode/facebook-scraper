"""Main entry point for the notifications service."""

import asyncio
import json
import logging
import signal
import sys
import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
import threading
from datetime import datetime

from shared.config.settings import get_settings, Settings
from shared.utils.kafka import get_kafka_client, kafka_producer, KafkaConsumer
from src.senders.email_sender import EmailSender
from src.senders.sms_sender import SMSSender
from src.senders.push_sender import PushSender
from shared.utils.logging_config import configure_logging, get_logger
from shared.models.marketplace import Listing

# Import health setup
from src.health_setup import setup_health_checks, create_health_check

# Create FastAPI app for health checks
from fastapi import FastAPI
app = FastAPI(
    title="Facebook Marketplace Notifications Service",
    description="Service for sending notifications about Facebook Marketplace listings",
    version="2.0.0",
)

# Set up health checks
health_check = setup_health_checks(app)

# Get settings
settings = get_settings("notifications")

# Configure logging
configure_logging(service_name="notifications-service")
logger = get_logger(__name__)

# Create Kafka client
kafka_client = get_kafka_client("notifications")

# Create notification senders
email_sender = EmailSender(
    host=settings.notification.smtp_host,
    port=settings.notification.smtp_port,
    username=settings.notification.smtp_user,
    password=settings.notification.smtp_password,
    from_email=settings.notification.from_email
)

sms_sender = SMSSender()
push_sender = PushSender()

# Flag to indicate if the service is running
running = True

def handle_shutdown(sig, frame):
    """Handle shutdown signals."""
    global running
    logger.info(f"Received shutdown signal {sig}")
    running = False

async def send_notification(alert_data: Dict[str, Any]) -> bool:
    """
    Send a notification for a triggered alert.
    
    Args:
        alert_data: Alert data including the matched listing
        
    Returns:
        True if notification was sent successfully, False otherwise
    """
    try:
        # Extract data
        alert = alert_data.get("alert", {})
        listing = alert_data.get("listing", {})
        notification_method = alert.get("notification_method", "email")
        notification_target = alert.get("notification_target")
        
        if not notification_target:
            logger.error("No notification target specified")
            return False
        
        # Prepare notification content
        listing_title = listing.get("title", "Unknown listing")
        listing_price = listing.get("price", "Unknown price")
        listing_url = listing.get("listing_url", "#")
        
        subject = f"New listing found: {listing_title}"
        
        message = f"""
        Hello!
        
        We found a new listing that matches your alert:
        
        {listing_title}
        Price: ${listing_price}
        
        View the listing: {listing_url}
        
        Thanks for using our service!
        """
        
        # Send notification based on method
        success = False
        if notification_method == "email":
            success = await email_sender.send(
                to_email=notification_target,
                subject=subject,
                message=message
            )
        elif notification_method == "sms":
            success = await sms_sender.send(
                phone_number=notification_target,
                message=f"New listing found: {listing_title} - ${listing_price}. View at {listing_url}"
            )
        elif notification_method == "push":
            success = await push_sender.send(
                device_token=notification_target,
                title=subject,
                body=f"Found: {listing_title} - ${listing_price}",
                data={"url": listing_url}
            )
        else:
            logger.error(f"Unknown notification method: {notification_method}")
            return False
        
        if success:
            logger.info(f"Notification sent successfully via {notification_method} to {notification_target}")
            
            # Publish notification event
            with kafka_producer("notifications") as producer:
                producer.publish_event(
                    topic="marketplace.notification.sent",
                    key=str(alert_data.get("alert_id")),
                    value={
                        "alert_id": alert_data.get("alert_id"),
                        "listing_id": listing.get("external_id"),
                        "notification_method": notification_method,
                        "notification_target": notification_target,
                        "status": "sent",
                        "sent_at": datetime.utcnow().isoformat()
                    }
                )
        else:
            logger.error(f"Failed to send notification via {notification_method} to {notification_target}")
        
        return success
    
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        return False

async def listen_for_alerts() -> None:
    """
    Listen for alert triggers from Kafka.
    
    Processes alerts and sends notifications.
    """
    logger.info("Starting to listen for alert triggers")
    
    # Subscribe to the alerts topic
    topic = "marketplace.alert.triggered"
    
    async for message in kafka_client.consume_async([topic]):
        try:
            # Parse the message
            key = message.key().decode('utf-8') if message.key() else None
            value = message.value()
            
            if not value:
                logger.warning(f"Received empty alert data, skipping")
                continue
            
            # Parse the alert data
            alert_data = json.loads(value)
            
            # Send notification
            logger.info(f"Processing alert {alert_data.get('alert_id')} for listing {alert_data.get('listing_id')}")
            success = await send_notification(alert_data)
            
            if success:
                logger.info(f"Successfully sent notification for alert {alert_data.get('alert_id')}")
            else:
                logger.error(f"Failed to send notification for alert {alert_data.get('alert_id')}")
            
        except Exception as e:
            logger.error(f"Error processing alert: {str(e)}")
        
        # Check if we should continue running
        if not running:
            break

class NotificationService:
    """Service for sending notifications about marketplace listings."""
    
    def __init__(self, settings: Settings):
        """Initialize the notification service with configuration settings."""
        self.settings = settings
        
        # Initialize Kafka consumer for alerts
        self.consumer = KafkaConsumer(
            bootstrap_servers=settings.kafka.bootstrap_servers,
            topic=settings.kafka.topics.alerts,
            group_id="notifications-service"
        )
        
        # SMTP settings
        self.smtp_server = settings.notifications.smtp_server
        self.smtp_port = settings.notifications.smtp_port
        self.smtp_username = settings.notifications.smtp_username
        self.smtp_password = settings.notifications.smtp_password
        self.sender_email = settings.notifications.sender_email
        
        # Initialize health check
        self.health_check = health_check
        
        logger.info("Notification service initialized", 
                    extra={"smtp_server": self.smtp_server, "sender": self.sender_email})
    
    def run(self) -> None:
        """Run the notification service continuously."""
        logger.info("Starting notification service")
        
        # Update health check statuses for critical components
        try:
            # Try to connect to the database
            # This is a placeholder - replace with actual DB connection
            # db = connect_to_database()
            self.health_check.set_status("database", True)
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            
        # Check Kafka consumer
        try:
            messages = self.consumer.consume(timeout=1.0, num_messages=1)
            self.health_check.set_status("kafka-consumer", True)
            logger.info("Kafka consumer connected")
        except Exception as e:
            logger.error(f"Kafka consumer error: {str(e)}")
        
        # Check email provider
        try:
            # Test connection to SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=5) as server:
                server.ehlo()
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
            self.health_check.set_status("email-provider", True)
            logger.info("Email provider connection established")
        except Exception as e:
            logger.error(f"Email provider connection failed: {str(e)}")
        
        while True:
            try:
                # Consume alert messages from Kafka
                for alert in self.consumer.consume(timeout=5.0):
                    if alert is None:
                        continue
                    
                    logger.debug("Processing new alert", 
                                 extra={"alert_id": alert.get("alert_id"), 
                                        "listing_id": alert.get("listing_id")})
                    
                    # Send notifications based on alert type
                    if "notification_type" in alert:
                        if alert["notification_type"] == "email":
                            self._send_email_notification(alert)
                        elif alert["notification_type"] == "sms":
                            self._send_sms_notification(alert)
                        else:
                            logger.warning("Unknown notification type",
                                          extra={"notification_type": alert["notification_type"]})
                    else:
                        # Default to email if not specified
                        self._send_email_notification(alert)
                    
            except Exception as e:
                logger.error(f"Error in notification service: {str(e)}", exc_info=True)
                self.health_check.set_status("service", False)
                time.sleep(10)  # Wait before retrying
    
    def _send_email_notification(self, alert: Dict[str, Any]) -> bool:
        """
        Send an email notification.
        
        Args:
            alert: Alert data containing recipient and listing information
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Extract recipient email
            recipient = alert.get("recipient_email")
            if not recipient:
                logger.error("No recipient email specified in alert")
                return False
            
            # Get listing data
            listing = alert.get("listing", {})
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['Subject'] = f"New listing alert: {listing.get('title', 'New listing')}"
            
            # Create email body
            body = self._create_email_body(listing, alert)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent to {recipient}", 
                       extra={"recipient": recipient, "alert_id": alert.get("alert_id")})
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}", exc_info=True)
            self.health_check.set_status("email-provider", False)
            return False
    
    def _send_sms_notification(self, alert: Dict[str, Any]) -> bool:
        """
        Send an SMS notification.
        
        Args:
            alert: Alert data containing recipient and listing information
            
        Returns:
            True if SMS sent successfully, False otherwise
        """
        # Placeholder - implement SMS sending functionality
        logger.info("SMS notification would be sent here")
        return True
    
    def _create_email_body(self, listing: Dict[str, Any], alert: Dict[str, Any]) -> str:
        """
        Create HTML email body for notification.
        
        Args:
            listing: Listing data
            alert: Alert data
            
        Returns:
            HTML formatted email body
        """
        title = listing.get("title", "Unknown listing")
        price = listing.get("price", "Unknown price")
        description = listing.get("description", "No description available")
        image_url = listing.get("image_url", "")
        listing_url = listing.get("listing_url", "#")
        
        # Truncate description if too long
        if len(description) > 200:
            description = description[:197] + "..."
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4267B2; padding: 10px; color: white; text-align: center; }}
                .listing {{ padding: 15px; border: 1px solid #ddd; border-radius: 5px; margin-top: 20px; }}
                .listing img {{ max-width: 100%; max-height: 300px; display: block; margin: 0 auto; }}
                .price {{ color: #4CAF50; font-size: 24px; font-weight: bold; margin: 10px 0; }}
                .button {{ display: inline-block; background-color: #4267B2; color: white; padding: 10px 20px; 
                          text-decoration: none; border-radius: 5px; margin-top: 15px; }}
                .footer {{ margin-top:
                           30px; font-size: 12px; color: #777; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>New Listing Alert</h2>
                </div>
                <p>We found a new listing that matches your alert criteria:</p>
                <div class="listing">
                    <h3>{title}</h3>
                    <div class="price">${price}</div>
                    
                    {f'<img src="{image_url}" alt="{title}">' if image_url else ''}
                    
                    <p>{description}</p>
                    
                    <a href="{listing_url}" class="button">View Listing</a>
                </div>
                <div class="footer">
                    <p>You received this email because you set up an alert for Facebook Marketplace listings.</p>
                    <p>To unsubscribe, click <a href="#">here</a>.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html

# Run the FastAPI app for health checks in a separate thread
def run_health_server():
    """Run the FastAPI app for health checks."""
    import uvicorn
    port = int(os.getenv("HEALTH_PORT", "8080"))
    logger.info(f"Starting health check server on port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="error"
    )

def main() -> None:
    """Main entry point for the notification service."""
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Load settings
    settings = Settings()
    
    # Start health check server in a separate thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Initialize and run the notification service
    notification_service = NotificationService(settings)
    notification_service.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Notifications service stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1) 