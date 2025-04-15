# Testing Documentation

## Overview

This document outlines the testing strategy and practices for the Facebook Marketplace Scraper project. The testing approach is designed to ensure code quality, reliability, and maintainability across all microservices.

## Testing Layers

The project implements a comprehensive testing strategy with multiple layers:

### Unit Testing

Unit tests focus on testing individual components in isolation:

- **Scope**: Individual functions, classes, and methods
- **Tools**: pytest, unittest.mock
- **Coverage Target**: 80% code coverage minimum
- **Location**: `tests/unit/` directory in each service

Example unit test for a utility function:

```python
# tests/unit/test_utils.py
import pytest
from backend.shared.utils.data_formatting import format_price

def test_format_price_with_valid_input():
    # Test with valid input
    assert format_price(10.5) == "$10.50"
    assert format_price(1000) == "$1,000.00"
    
def test_format_price_with_different_currency():
    # Test with different currency
    assert format_price(10.5, currency="EUR") == "€10.50"
    
def test_format_price_with_invalid_input():
    # Test with invalid input
    with pytest.raises(ValueError):
        format_price("not a number")
```

### Integration Testing

Integration tests verify that components work together correctly:

- **Scope**: Interactions between components and services
- **Tools**: pytest, TestContainers
- **Coverage**: Service interfaces and data flows
- **Location**: `tests/integration/` directory in each service

Example integration test for database operations:

```python
# tests/integration/test_database.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from backend.shared.models.base import Base
from backend.services.api.src.repositories.listing_repository import ListingRepository
from backend.shared.models.marketplace import Listing

@pytest.fixture
async def db_engine():
    # Create test database engine
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def listing_repository(db_engine):
    return ListingRepository(db_engine)

@pytest.mark.asyncio
async def test_create_and_retrieve_listing(listing_repository):
    # Create test listing
    listing = Listing(
        title="Test Listing",
        price=100.0,
        description="Test description",
        location="Test location",
        external_id="ext123"
    )
    
    # Save to database
    saved_id = await listing_repository.create(listing)
    
    # Retrieve and verify
    retrieved = await listing_repository.get_by_id(saved_id)
    
    assert retrieved is not None
    assert retrieved.title == "Test Listing"
    assert retrieved.price == 100.0
```

### API Testing

API tests validate the external HTTP interfaces:

- **Scope**: REST API endpoints
- **Tools**: pytest, FastAPI TestClient
- **Coverage**: Request/response validation, status codes, error handling
- **Location**: `tests/api/` directory in the API service

Example API test:

```python
# tests/api/test_listings_api.py
from fastapi.testclient import TestClient
import pytest
from backend.services.api.src.main import app
from backend.shared.auth.jwt import create_test_token

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers():
    token = create_test_token({"sub": "test_user", "role": "user"})
    return {"Authorization": f"Bearer {token}"}

def test_get_listings(client, auth_headers):
    response = client.get("/listings", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "pagination" in data

def test_get_listing_detail(client, auth_headers):
    # Assuming listing with ID 1 exists
    response = client.get("/listings/1", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert "title" in data
    assert "price" in data
```

### End-to-End Testing

E2E tests verify complete user workflows:

- **Scope**: Full system functionality from user perspective
- **Tools**: pytest, Playwright
- **Coverage**: Critical user journeys
- **Location**: `tests/e2e/` directory at the project root

Example E2E test:

```python
# tests/e2e/test_search_flow.py
import pytest
from playwright.sync_api import Page, expect

def test_search_and_view_listing(page: Page, base_url: str):
    # Navigate to home page
    page.goto(base_url)
    
    # Search for a product
    page.fill('[data-testid="search-input"]', "iphone")
    page.click('[data-testid="search-button"]')
    
    # Wait for results and click on first listing
    page.wait_for_selector('[data-testid="listing-card"]')
    page.click('[data-testid="listing-card"]:first-child')
    
    # Verify listing details page loaded
    expect(page).to_have_url(f"{base_url}/listings/*")
    expect(page.locator('[data-testid="listing-title"]')).to_be_visible()
    expect(page.locator('[data-testid="listing-price"]')).to_be_visible()
```

## Mocking and Test Doubles

The project uses various test doubles to isolate components:

### Mock External Services

```python
# Example of mocking Kafka producer
@pytest.fixture
def mock_kafka_producer(monkeypatch):
    mock_producer = MagicMock()
    monkeypatch.setattr(
        "backend.shared.utils.kafka.KafkaProducer",
        MagicMock(return_value=mock_producer)
    )
    return mock_producer

def test_publish_listing(mock_kafka_producer):
    service = ListingService()
    service.publish_listing({"id": 1, "title": "Test"})
    
    # Verify the producer was called correctly
    mock_kafka_producer.produce.assert_called_once()
    args = mock_kafka_producer.produce.call_args[0]
    assert args[0] == "marketplace.listings"  # Topic
    assert "id" in args[1]  # Message
```

### Fake Database

```python
# Example of in-memory database for testing
@pytest.fixture
async def in_memory_db():
    # Create SQLite in-memory database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Yield session
    async with async_session() as session:
        yield session
    
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

## Test Data Management

### Test Fixtures

The project uses pytest fixtures to manage test data:

```python
# tests/conftest.py
import pytest
from datetime import datetime, timedelta

@pytest.fixture
def sample_listings():
    """Generate sample listings for tests"""
    return [
        {
            "id": 1,
            "title": "iPhone 12 Pro",
            "price": 699.99,
            "description": "Used iPhone in good condition",
            "created_at": datetime.utcnow(),
            "category": "electronics",
            "location": "San Francisco, CA"
        },
        {
            "id": 2,
            "title": "Dining Table with Chairs",
            "price": 250.00,
            "description": "Wooden dining table with 4 chairs",
            "created_at": datetime.utcnow() - timedelta(days=2),
            "category": "furniture",
            "location": "New York, NY"
        }
    ]
```

### Factory Pattern

For complex test data, the project uses factory patterns:

```python
# tests/factories.py
from datetime import datetime
import factory
from backend.shared.models.marketplace import Listing, User

class UserFactory(factory.Factory):
    class Meta:
        model = User
        
    id = factory.Sequence(lambda n: n)
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    created_at = factory.LazyFunction(datetime.utcnow)
    role = "user"

class ListingFactory(factory.Factory):
    class Meta:
        model = Listing
        
    id = factory.Sequence(lambda n: n)
    title = factory.Sequence(lambda n: f"Listing {n}")
    price = factory.Faker("pyfloat", min_value=10, max_value=1000)
    description = factory.Faker("paragraph")
    created_at = factory.LazyFunction(datetime.utcnow)
    category = factory.Iterator(["electronics", "furniture", "clothing"])
    location = factory.Faker("city")
    seller = factory.SubFactory(UserFactory)
```

## Testing Infrastructure

### Continuous Integration

Tests run automatically in the CI/CD pipeline:

- Pull request checks run unit and integration tests
- Nightly builds run full test suite including E2E tests
- Code coverage reports are generated and tracked

### Test Command Examples

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run specific test file
pytest tests/unit/test_utils.py

# Run with coverage
pytest --cov=backend

# Run and generate HTML coverage report
pytest --cov=backend --cov-report=html
```

## Test Organization

The test directory structure mirrors the application structure:

```
backend/
├── services/
│   ├── api/
│   │   ├── src/
│   │   └── tests/
│   │       ├── unit/
│   │       ├── integration/
│   │       └── api/
│   ├── scraper/
│   │   ├── src/
│   │   └── tests/
│   │       ├── unit/
│   │       └── integration/
│   ├── processor/
│   │   ├── src/
│   │   └── tests/
│   │       ├── unit/
│   │       └── integration/
│   └── notifications/
│       ├── src/
│       └── tests/
│           ├── unit/
│           └── integration/
├── shared/
│   ├── models/
│   ├── utils/
│   └── tests/
│       ├── unit/
│       └── integration/
└── tests/
    ├── e2e/
    ├── performance/
    └── security/
```

## Testing Guidelines

### Best Practices

1. **Test-Driven Development**: Write tests before implementation when feasible
2. **Isolated Tests**: Each test should be independent and not rely on other tests
3. **Descriptive Names**: Use clear, descriptive test names that explain the scenario
4. **Arrange, Act, Assert**: Structure tests with clear setup, action, and verification
5. **Test Edge Cases**: Include tests for boundary conditions and error scenarios

### What to Test

- **Business Logic**: Core functionality and business rules
- **Edge Cases**: Boundary conditions and exceptional inputs
- **Error Handling**: How the system responds to errors
- **Performance Critical Paths**: Key performance-sensitive operations
- **Security Controls**: Authentication, authorization, and data validation

## Performance Testing

The project includes performance tests for critical operations:

- **Load Tests**: Verify system behavior under expected load
- **Stress Tests**: Identify breaking points under extreme conditions
- **Endurance Tests**: Verify system stability over extended periods

Example performance test:

```python
# tests/performance/test_api_performance.py
import pytest
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login to get auth token
        response = self.client.post("/auth/login", json={
            "username": "performance_test_user",
            "password": "test_password"
        })
        data = response.json()
        self.token = data["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(10)
    def get_listings(self):
        self.client.get("/listings", headers=self.headers)
    
    @task(3)
    def search_listings(self):
        self.client.get("/listings?q=iphone", headers=self.headers)
    
    @task(1)
    def get_listing_detail(self):
        # Get a random listing by ID
        listing_id = self.random_listing_id()
        self.client.get(f"/listings/{listing_id}", headers=self.headers)
```

## Security Testing

Security-focused tests verify the system's defense mechanisms:

- **Authentication Tests**: Verify login, token validation, and session management
- **Authorization Tests**: Ensure proper access control
- **Input Validation**: Test protection against injection and malformed inputs
- **Rate Limiting**: Verify throttling mechanisms

## Related Documentation

- [Architecture Overview](architecture.md)
- [API Documentation](api.md)
- [Security Documentation](security.md)
