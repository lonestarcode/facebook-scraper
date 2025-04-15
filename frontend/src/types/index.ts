export interface Listing {
  id: number;
  listing_id: string;
  title: string;
  price: number;
  description: string;
  location: string;
  category: string;
  seller_id: string;
  listing_url: string;
  images: ListingImage[];
  created_at: string;
  updated_at: string;
  analysis?: ListingAnalysis;
}

export interface ListingImage {
  url: string;
  alt?: string;
}

export interface ListingAnalysis {
  quality_score: number;
  keywords: string[];
  category_confidence: number;
  confidence: number;
}

export interface PriceAlert {
  id: number;
  user_id: string;
  category: string;
  max_price: number;
  keywords: string[];
  notify_email: string;
  notify_webhook?: string;
  created_at: string;
  is_active: boolean;
}

export interface FilterOptions {
  category?: string;
  minPrice?: number;
  maxPrice?: number;
  location?: string;
  keywords?: string[];
} 