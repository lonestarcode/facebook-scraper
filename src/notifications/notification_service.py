from typing import List, Dict
import aiohttp
import smtplib
from email.mime.text import MIMEText
from src.database.models import PriceAlert, AlertNotification, MarketplaceListing
from src.logging.logger import get_logger

logger = get_logger(__name__)

class NotificationService:
    def __init__(self, smtp_config: Dict):
        self.smtp_config = smtp_config
        
    async def process_new_listing(self, listing: MarketplaceListing, session) -> None:
        """Check if new listing matches any alerts and send notifications"""
        try:
            # Query relevant price alerts
            alerts = await session.query(PriceAlert).filter(
                PriceAlert.category == listing.category,
                PriceAlert.max_price >= listing.price,
                PriceAlert.is_active == True
            ).all()
            
            for alert in alerts:
                if self._matches_keywords(listing.title, alert.keywords):
                    await self._send_notification(alert, listing, session)
                    
        except Exception as e:
            logger.error(f"Error processing listing for alerts: {str(e)}")
            
    def _matches_keywords(self, title: str, keywords: List[str]) -> bool:
        """Check if listing title matches alert keywords"""
        title_lower = title.lower()
        return any(keyword.lower() in title_lower for keyword in keywords)
        
    async def _send_notification(self, alert: PriceAlert, listing: MarketplaceListing, session) -> None:
        """Send notification through configured channels"""
        try:
            # Send email notification
            if alert.notify_email:
                await self._send_email_notification(alert, listing)
                
            # Send webhook notification
            if alert.notify_webhook:
                await self._send_webhook_notification(alert, listing)
                
            # Record notification
            notification = AlertNotification(
                alert_id=alert.id,
                listing_id=listing.id,
                notification_type='email' if alert.notify_email else 'webhook'
            )
            session.add(notification)
            await session.commit()
            
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            
    async def _send_email_notification(self, alert: PriceAlert, listing: MarketplaceListing) -> None:
        """Send email notification"""
        try:
            msg = MIMEText(
                f"New listing matching your alert!\n\n"
                f"Title: {listing.title}\n"
                f"Price: ${listing.price}\n"
                f"Location: {listing.location}\n"
                f"URL: {listing.listing_url}"
            )
            msg['Subject'] = f"New Marketplace Listing: {listing.title}"
            msg['From'] = self.smtp_config['from_email']
            msg['To'] = alert.notify_email
            
            with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port']) as server:
                server.starttls()
                server.login(self.smtp_config['username'], self.smtp_config['password'])
                server.send_message(msg)
                
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            
    async def _send_webhook_notification(self, alert: PriceAlert, listing: MarketplaceListing) -> None:
        """Send webhook notification"""
        try:
            payload = {
                'alert_id': alert.id,
                'listing': {
                    'id': listing.id,
                    'title': listing.title,
                    'price': listing.price,
                    'location': listing.location,
                    'url': listing.listing_url
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(alert.notify_webhook, json=payload) as response:
                    if response.status != 200:
                        logger.error(f"Webhook notification failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error sending webhook notification: {str(e)}") 