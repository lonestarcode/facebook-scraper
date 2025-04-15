"""Analyzer for marketplace listings."""

import logging
import re
from typing import Dict, Any, List, Tuple, Optional
import asyncio
from datetime import datetime

logger = logging.getLogger("processor.analyzer")

class ListingAnalyzer:
    """
    Analyzer for marketplace listings.
    
    Performs various analyses on listings:
    - Quality scoring
    - Keyword extraction
    - Price analysis
    - Category verification
    - Spam detection
    """
    
    def __init__(self):
        """Initialize the listing analyzer."""
        # Common spam keywords
        self.spam_keywords = [
            "wholesale", "drop.?ship", "msg.?me", "text.?me", "contact.?me",
            "whatsapp", "telegram", "not.?available", "click.?link",
            "click.?here", "dm.?me", "direct.?message", "\\$\\$\\$"
        ]
        self.spam_pattern = re.compile("|".join(self.spam_keywords), re.IGNORECASE)
        
        # Keywords to extract by category
        self.category_keywords = {
            "furniture": ["wood", "leather", "fabric", "sofa", "chair", "table", "bed", "desk", "shelf"],
            "electronics": ["screen", "inch", "gb", "tb", "memory", "processor", "camera", "battery"],
            "vehicles": ["mileage", "miles", "gas", "electric", "transmission", "engine", "year"],
            "clothing": ["size", "small", "medium", "large", "xl", "cotton", "leather", "wool"]
        }
        
        # Category classification patterns
        self.category_patterns = {
            "furniture": re.compile(r"(sofa|chair|table|desk|drawers|cabinet|bed|mattress|couch|furniture)", re.IGNORECASE),
            "electronics": re.compile(r"(phone|laptop|computer|tv|television|headphone|camera|console|gaming|electronic)", re.IGNORECASE),
            "vehicles": re.compile(r"(car|truck|van|suv|bike|motorcycle|scooter|vehicle)", re.IGNORECASE),
            "clothing": re.compile(r"(shirt|pants|dress|jacket|coat|shoes|boots|clothing|wear|apparel)", re.IGNORECASE),
            "jewelry": re.compile(r"(ring|necklace|bracelet|earring|gold|silver|diamond|jewelry)", re.IGNORECASE),
            "toys": re.compile(r"(toy|game|puzzle|lego|doll|figure|kids|children)", re.IGNORECASE),
            "tools": re.compile(r"(tool|drill|saw|hammer|screwdriver|workbench|equipment)", re.IGNORECASE),
            "appliances": re.compile(r"(refrigerator|fridge|washer|dryer|stove|oven|microwave|dishwasher|appliance)", re.IGNORECASE)
        }
    
    async def analyze(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a marketplace listing.
        
        Args:
            listing_data: Raw listing data
            
        Returns:
            Dictionary with analysis results
        """
        # Run analyses concurrently
        title = listing_data.get("title", "")
        description = listing_data.get("description", "")
        price = listing_data.get("price")
        category = listing_data.get("category")
        
        tasks = [
            self._analyze_quality(title, description, price),
            self._extract_keywords(title, description, category),
            self._analyze_price(price, category),
            self._verify_category(title, description, category),
            self._detect_spam(title, description)
        ]
        
        # Wait for all analyses to complete
        quality_score, keywords, price_analysis, category_info, spam_info = await asyncio.gather(*tasks)
        
        # Combine all analyses into a single result
        return {
            "quality_score": quality_score,
            "keywords": keywords,
            "price_analysis": price_analysis,
            "category": category_info,
            "spam_detection": spam_info,
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    async def _analyze_quality(self, title: str, description: str, price: Optional[float]) -> float:
        """
        Analyze the quality of a listing.
        
        Args:
            title: Listing title
            description: Listing description
            price: Listing price
            
        Returns:
            Quality score between 0 and 1
        """
        score = 0.0
        reasons = []
        
        # Check title length (20-80 characters is ideal)
        title_length = len(title)
        if title_length < 10:
            score += 0.2
            reasons.append("title_too_short")
        elif 10 <= title_length < 20:
            score += 0.5
            reasons.append("title_short")
        elif 20 <= title_length <= 80:
            score += 1.0
            reasons.append("title_good_length")
        else:  # > 80
            score += 0.7
            reasons.append("title_too_long")
        
        # Check description length (50-1000 characters is ideal)
        desc_length = len(description) if description else 0
        if desc_length < 20:
            score += 0.1
            reasons.append("description_too_short")
        elif 20 <= desc_length < 50:
            score += 0.3
            reasons.append("description_short")
        elif 50 <= desc_length <= 1000:
            score += 1.0
            reasons.append("description_good_length")
        else:  # > 1000
            score += 0.6
            reasons.append("description_too_long")
        
        # Check if price is provided
        if price is not None:
            score += 1.0
            reasons.append("has_price")
        else:
            score += 0.0
            reasons.append("no_price")
        
        # Calculate final score (0-1 range)
        final_score = score / 3.0
        
        return final_score
    
    async def _extract_keywords(self, title: str, description: str, category: Optional[str]) -> List[str]:
        """
        Extract keywords from the listing.
        
        Args:
            title: Listing title
            description: Listing description
            category: Listing category
            
        Returns:
            List of keywords
        """
        # Combine title and description
        text = f"{title} {description}".lower()
        
        # Extract category-specific keywords if category is known
        category_specific_keywords = []
        if category and category.lower() in self.category_keywords:
            patterns = self.category_keywords[category.lower()]
            for pattern in patterns:
                if re.search(r"\b" + re.escape(pattern) + r"\b", text, re.IGNORECASE):
                    category_specific_keywords.append(pattern)
        
        # Extract general keywords (simple approach)
        # In a real implementation, you might use NLP techniques like TF-IDF
        words = re.findall(r'\b[a-z]{4,}\b', text)
        word_counts = {}
        for word in words:
            if word not in word_counts:
                word_counts[word] = 0
            word_counts[word] += 1
        
        # Get the top 10 most frequent words
        general_keywords = sorted(word_counts.keys(), key=lambda k: word_counts[k], reverse=True)[:10]
        
        # Combine keywords, removing duplicates
        all_keywords = list(set(category_specific_keywords + general_keywords))
        
        return all_keywords[:15]  # Limit to 15 keywords
    
    async def _analyze_price(self, price: Optional[float], category: Optional[str]) -> Dict[str, Any]:
        """
        Analyze the listing price.
        
        Args:
            price: Listing price
            category: Listing category
            
        Returns:
            Price analysis results
        """
        if price is None:
            return {
                "status": "unknown",
                "reason": "no_price"
            }
        
        # These would typically come from a database of market prices
        # For this example, we'll use hardcoded values
        category_price_ranges = {
            "furniture": (50, 2000),
            "electronics": (25, 2000),
            "vehicles": (500, 50000),
            "clothing": (5, 500),
            "jewelry": (20, 5000),
            "toys": (5, 200),
            "tools": (10, 500),
            "appliances": (50, 2000)
        }
        
        # Get the price range for the category, or use a default range
        if category and category.lower() in category_price_ranges:
            min_price, max_price = category_price_ranges[category.lower()]
        else:
            min_price, max_price = (10, 5000)  # Default range
        
        # Determine if price is reasonable
        if price < min_price * 0.5:
            status = "suspiciously_low"
            reason = "price_below_market"
        elif price < min_price:
            status = "below_average"
            reason = "price_below_average"
        elif min_price <= price <= max_price:
            status = "reasonable"
            reason = "price_within_range"
        elif price <= max_price * 2:
            status = "above_average"
            reason = "price_above_average"
        else:
            status = "suspiciously_high"
            reason = "price_above_market"
        
        return {
            "status": status,
            "reason": reason,
            "reference_range": (min_price, max_price)
        }
    
    async def _verify_category(self, title: str, description: str, provided_category: Optional[str]) -> Dict[str, Any]:
        """
        Verify and suggest category for the listing.
        
        Args:
            title: Listing title
            description: Listing description
            provided_category: Category provided in the listing
            
        Returns:
            Category verification results
        """
        # Combine title and description
        text = f"{title} {description}".lower()
        
        # Score each category based on keyword matches
        category_scores = {}
        for category, pattern in self.category_patterns.items():
            matches = pattern.findall(text)
            score = len(matches)
            category_scores[category] = score
        
        # Get the most likely category
        if category_scores:
            suggested_category = max(category_scores.items(), key=lambda x: x[1])
            confidence = min(1.0, suggested_category[1] / 3.0)  # Cap at 1.0
        else:
            suggested_category = (None, 0)
            confidence = 0.0
        
        # Compare with provided category
        if provided_category and provided_category.lower() in self.category_patterns:
            provided_score = category_scores.get(provided_category.lower(), 0)
            if provided_score > 0:
                match = "confirmed" if provided_score >= suggested_category[1] else "possible"
            else:
                match = "unconfirmed"
        else:
            match = "unknown"
        
        return {
            "provided_category": provided_category,
            "suggested_category": suggested_category[0],
            "confidence": confidence,
            "match": match
        }
    
    async def _detect_spam(self, title: str, description: str) -> Dict[str, Any]:
        """
        Detect spam patterns in the listing.
        
        Args:
            title: Listing title
            description: Listing description
            
        Returns:
            Spam detection results
        """
        # Combine title and description
        text = f"{title} {description}".lower()
        
        # Check for spam patterns
        spam_matches = self.spam_pattern.findall(text)
        is_spam = len(spam_matches) > 0
        
        # Additional spam indicators
        has_many_symbols = len(re.findall(r'[!$*+#]', text)) > 5
        has_excessive_caps = len(re.findall(r'\b[A-Z]{4,}\b', title)) > 0
        has_repeated_phrases = len(re.findall(r'(\b\w+\b)(?:\s+\w+){0,5}\s+\1\b', text)) > 2
        
        # Overall spam score
        spam_score = len(spam_matches) * 0.3
        spam_score += 0.2 if has_many_symbols else 0
        spam_score += 0.2 if has_excessive_caps else 0
        spam_score += 0.3 if has_repeated_phrases else 0
        
        # Limit to range 0-1
        spam_score = min(1.0, spam_score)
        
        return {
            "is_spam": is_spam,
            "spam_score": spam_score,
            "spam_indicators": {
                "spam_keywords": bool(spam_matches),
                "excessive_symbols": has_many_symbols,
                "excessive_caps": has_excessive_caps,
                "repeated_phrases": has_repeated_phrases
            },
            "matched_patterns": spam_matches
        } 