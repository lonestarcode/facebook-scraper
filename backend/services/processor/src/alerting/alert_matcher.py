"""Alert matcher for finding listings that match user alerts."""

import logging
import re
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, not_

from shared.models.marketplace import PriceAlert

logger = logging.getLogger("processor.alert_matcher")

class AlertMatcher:
    """
    Alert matcher for finding listings that match user alerts.
    
    Checks listings against various alert criteria:
    - Price range
    - Category
    - Search terms
    - Location
    """
    
    def __init__(self):
        """Initialize the alert matcher."""
        pass
    
    async def find_matches(self, listing_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find alerts that match a listing.
        
        Args:
            listing_data: Listing data to check
            
        Returns:
            List of matching alerts with match reasons
        """
        try:
            # In a production system, we would query the database for alerts
            # For this example, we'll simulate database access
            # In a real implementation, this would be a call to the database
            
            # Get alerts from database (simulated)
            alerts = await self._get_alerts_from_db()
            
            # Match the listing against each alert
            matches = []
            for alert in alerts:
                match_result = await self._check_alert_match(listing_data, alert)
                if match_result["is_match"]:
                    matches.append({
                        "alert_id": alert["id"],
                        "user_id": alert["user_id"],
                        "reason": match_result["reason"],
                        "alert": alert
                    })
            
            logger.info(f"Found {len(matches)} matching alerts for listing {listing_data.get('external_id')}")
            return matches
            
        except Exception as e:
            logger.error(f"Error finding alert matches: {str(e)}")
            return []
    
    async def _get_alerts_from_db(self) -> List[Dict[str, Any]]:
        """
        Get active alerts from the database.
        
        This is a simulated implementation. In a real system, this would query the database.
        
        Returns:
            List of active alerts
        """
        # Simulated alerts - in a real implementation, these would come from the database
        return [
            {
                "id": 1,
                "user_id": "00000000-0000-0000-0000-000000000001",
                "search_term": "leather sofa",
                "category": "furniture",
                "min_price": 100,
                "max_price": 1000,
                "location": "New York",
                "notification_method": "email",
                "notification_target": "user1@example.com",
                "is_active": True
            },
            {
                "id": 2,
                "user_id": "00000000-0000-0000-0000-000000000002",
                "search_term": None,
                "category": "electronics",
                "min_price": None,
                "max_price": 500,
                "location": None,
                "notification_method": "email",
                "notification_target": "user2@example.com",
                "is_active": True
            },
            {
                "id": 3,
                "user_id": "00000000-0000-0000-0000-000000000003",
                "search_term": "iphone",
                "category": None,
                "min_price": None,
                "max_price": None,
                "location": "Los Angeles",
                "notification_method": "email",
                "notification_target": "user3@example.com",
                "is_active": True
            }
        ]
    
    async def _check_alert_match(self, listing: Dict[str, Any], alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if a listing matches an alert.
        
        Args:
            listing: Listing data to check
            alert: Alert to check against
            
        Returns:
            Dictionary with match status and reason
        """
        matches = []
        non_matches = []
        
        # Check price range
        if alert["min_price"] is not None:
            if listing.get("price") is not None and listing["price"] >= alert["min_price"]:
                matches.append("min_price")
            else:
                non_matches.append("min_price")
        
        if alert["max_price"] is not None:
            if listing.get("price") is not None and listing["price"] <= alert["max_price"]:
                matches.append("max_price")
            else:
                non_matches.append("max_price")
        
        # Check category
        if alert["category"] is not None:
            if listing.get("category") is not None and alert["category"].lower() == listing["category"].lower():
                matches.append("category")
            else:
                # Check if the analyzer suggested this category
                analysis = listing.get("analysis", {})
                category_info = analysis.get("category", {})
                suggested = category_info.get("suggested_category")
                
                if suggested and alert["category"].lower() == suggested.lower():
                    matches.append("suggested_category")
                else:
                    non_matches.append("category")
        
        # Check search term
        if alert["search_term"] is not None:
            title = listing.get("title", "").lower()
            description = listing.get("description", "").lower()
            search_term = alert["search_term"].lower()
            
            # Check for exact match in title or description
            if search_term in title or search_term in description:
                matches.append("search_term_exact")
            else:
                # Check for word matches
                search_words = search_term.split()
                
                # Count how many words match
                matching_words = sum(1 for word in search_words if word in title or word in description)
                
                # If more than half of the words match, consider it a match
                if matching_words > len(search_words) / 2:
                    matches.append("search_term_partial")
                else:
                    # Check if any keyword matches
                    analysis = listing.get("analysis", {})
                    keywords = analysis.get("keywords", [])
                    
                    if any(word in search_term for word in keywords):
                        matches.append("search_term_keyword")
                    else:
                        non_matches.append("search_term")
        
        # Check location
        if alert["location"] is not None:
            if listing.get("location") is not None:
                # Check if location strings match (case insensitive, partial match)
                alert_location = alert["location"].lower()
                listing_location = listing["location"].lower()
                
                if alert_location in listing_location or listing_location in alert_location:
                    matches.append("location")
                else:
                    non_matches.append("location")
            else:
                non_matches.append("location")
        
        # Determine overall match
        # For an alert to match, all specified criteria must match
        is_match = len(non_matches) == 0 and len(matches) > 0
        
        # Determine the match reason
        if is_match:
            reason = ", ".join(matches)
        else:
            reason = f"Failed to match on: {', '.join(non_matches)}"
        
        return {
            "is_match": is_match,
            "reason": reason,
            "matching_criteria": matches,
            "non_matching_criteria": non_matches
        } 