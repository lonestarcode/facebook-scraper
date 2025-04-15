# API Documentation

## Overview

This document describes the REST API endpoints exposed by the Facebook Marketplace Scraper's API Service. The API provides access to marketplace listings, user alerts, and account management functionality.

## Base URL

```
https://api.marketplace-scraper.example.com/v2
```

## Authentication

### JWT Authentication

Most API endpoints require authentication using JSON Web Tokens (JWT).

- Token must be included in the `Authorization` header
- Format: `Bearer {token}`

Example:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Acquisition

Tokens can be obtained via the `/auth/login` endpoint.

## Rate Limiting

API requests are rate-limited based on the following rules:

- Anonymous requests: 30 requests per minute
- Authenticated requests: 100 requests per minute
- Batch operations: 10 requests per minute

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time (in seconds) until the rate limit resets

## Endpoints

### Authentication

#### POST /auth/login

Authenticates a user and issues a JWT token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Status Codes:**
- 200 OK: Authentication successful
- 401 Unauthorized: Invalid credentials
- 429 Too Many Requests: Rate limit exceeded

#### POST /auth/refresh

Refreshes an expired JWT token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
Same as login endpoint.

**Status Codes:**
- 200 OK: Token refresh successful
- 401 Unauthorized: Invalid refresh token
- 429 Too Many Requests: Rate limit exceeded

### Listings

#### GET /listings

Retrieves a paginated list of marketplace listings.

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `sort`: Sort field (options: price, date, relevance)
- `order`: Sort order (asc, desc)
- `category`: Filter by category
- `price_min`: Minimum price filter
- `price_max`: Maximum price filter
- `location`: Location filter (city or postal code)
- `distance`: Distance from location in km
- `q`: Search query

**Response:**
```json
{
  "items": [
    {
      "id": "listing123",
      "title": "Used iPhone 11 Pro",
      "description": "Great condition, includes charger",
      "price": 499.99,
      "currency": "USD",
      "location": "San Francisco, CA",
      "category": "Electronics",
      "subcategory": "Phones",
      "images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
      "attributes": {
        "condition": "Used - Good",
        "brand": "Apple",
        "model": "iPhone 11 Pro"
      },
      "seller": {
        "id": "user456",
        "name": "John Smith",
        "rating": 4.8
      },
      "created_at": "2023-05-15T14:30:00Z",
      "updated_at": "2023-05-16T09:15:00Z",
      "url": "https://facebook.com/marketplace/item/123456789"
    }
    // Additional listings...
  ],
  "pagination": {
    "current_page": 1,
    "per_page": 20,
    "total_items": 243,
    "total_pages": 13
  }
}
```

**Status Codes:**
- 200 OK: Request successful
- 400 Bad Request: Invalid parameters
- 401 Unauthorized: Authentication required
- 429 Too Many Requests: Rate limit exceeded

#### GET /listings/{id}

Retrieves a specific listing by ID.

**Response:**
Individual listing object as shown in the listings endpoint.

**Status Codes:**
- 200 OK: Request successful
- 401 Unauthorized: Authentication required
- 404 Not Found: Listing not found
- 429 Too Many Requests: Rate limit exceeded

### Alerts

#### GET /alerts

Retrieves user's saved alerts.

**Response:**
```json
{
  "items": [
    {
      "id": "alert123",
      "name": "iPhone deals",
      "query": "iphone",
      "criteria": {
        "category": "Electronics",
        "price_max": 600,
        "location": "San Francisco, CA",
        "distance": 25
      },
      "notification_settings": {
        "email": true,
        "sms": false,
        "frequency": "instant"
      },
      "created_at": "2023-04-10T08:45:00Z",
      "updated_at": "2023-04-12T16:20:00Z"
    }
    // Additional alerts...
  ]
}
```

**Status Codes:**
- 200 OK: Request successful
- 401 Unauthorized: Authentication required
- 429 Too Many Requests: Rate limit exceeded

#### POST /alerts

Creates a new alert.

**Request Body:**
```json
{
  "name": "MacBook deals",
  "query": "macbook pro",
  "criteria": {
    "category": "Electronics",
    "subcategory": "Computers",
    "price_max": 1200,
    "location": "San Francisco, CA",
    "distance": 50
  },
  "notification_settings": {
    "email": true,
    "sms": true,
    "frequency": "daily"
  }
}
```

**Response:**
Created alert object.

**Status Codes:**
- 201 Created: Alert created successfully
- 400 Bad Request: Invalid parameters
- 401 Unauthorized: Authentication required
- 429 Too Many Requests: Rate limit exceeded

#### PUT /alerts/{id}

Updates an existing alert.

**Request Body:**
Same format as POST /alerts

**Response:**
Updated alert object.

**Status Codes:**
- 200 OK: Alert updated successfully
- 400 Bad Request: Invalid parameters
- 401 Unauthorized: Authentication required
- 404 Not Found: Alert not found
- 429 Too Many Requests: Rate limit exceeded

#### DELETE /alerts/{id}

Deletes an alert.

**Status Codes:**
- 204 No Content: Alert deleted successfully
- 401 Unauthorized: Authentication required
- 404 Not Found: Alert not found
- 429 Too Many Requests: Rate limit exceeded

### User Account

#### GET /user/profile

Retrieves the user's profile information.

**Response:**
```json
{
  "id": "user456",
  "email": "user@example.com",
  "name": "John Smith",
  "created_at": "2023-01-15T10:30:00Z",
  "subscription": {
    "plan": "premium",
    "status": "active",
    "expires_at": "2024-01-15T10:30:00Z"
  },
  "notification_preferences": {
    "email": true,
    "sms": true,
    "push": false
  }
}
```

**Status Codes:**
- 200 OK: Request successful
- 401 Unauthorized: Authentication required
- 429 Too Many Requests: Rate limit exceeded

#### PUT /user/profile

Updates user profile information.

**Request Body:**
```json
{
  "name": "John Smith",
  "notification_preferences": {
    "email": true,
    "sms": false,
    "push": true
  }
}
```

**Response:**
Updated user profile.

**Status Codes:**
- 200 OK: Profile updated successfully
- 400 Bad Request: Invalid parameters
- 401 Unauthorized: Authentication required
- 429 Too Many Requests: Rate limit exceeded

### Real-time Updates

WebSocket endpoint for receiving real-time listing updates.

**Connection URL:**
```
wss://api.marketplace-scraper.example.com/v2/ws
```

**Authentication:**
- Include JWT token as query parameter: `?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

**Events:**

1. New listing matching alert:
```json
{
  "type": "alert_match",
  "data": {
    "alert_id": "alert123",
    "alert_name": "iPhone deals",
    "listing": {
      // Listing object
    }
  }
}
```

2. Price change on watched listing:
```json
{
  "type": "price_change",
  "data": {
    "listing_id": "listing123",
    "previous_price": 549.99,
    "current_price": 499.99,
    "currency": "USD",
    "percentage_change": -9.1
  }
}
```

## Error Handling

All API errors follow a standard format:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "The request contained invalid parameters",
    "details": [
      {
        "field": "price_max",
        "message": "Must be a positive number"
      }
    ]
  }
}
```

Common error codes:
- `invalid_request`: Request validation failed
- `authentication_required`: Authentication is needed
- `invalid_credentials`: Provided credentials are invalid
- `resource_not_found`: Requested resource does not exist
- `rate_limit_exceeded`: Too many requests
- `internal_error`: Server-side error

## API Versioning

The API is versioned through the URL path (`/v2`). When breaking changes are introduced, a new API version will be created. Previous versions remain supported according to the deprecation policy.

## CORS Policy

The API supports Cross-Origin Resource Sharing (CORS) for specific origins.

## Changelog

### v2.0.0 (2023-06-01)
- Added WebSocket support for real-time updates
- Expanded listing attributes
- Added subscription-based rate limiting
- Improved error responses

### v1.0.0 (2023-01-15)
- Initial API release
