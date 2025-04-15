# Security Documentation

## Overview

This document outlines the security measures, practices, and considerations implemented in the Facebook Marketplace Scraper application. It details authentication mechanisms, data protection strategies, API security, and other security-related aspects of the system.

## Authentication System

### JWT-Based Authentication

The system uses JSON Web Tokens (JWT) for authentication, implemented in `backend/shared/auth/jwt.py`:

```python
class JWTHandler:
    def __init__(self, secret_key: str, token_expire_minutes: int = 30):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.token_expire_minutes = token_expire_minutes
        
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """
        Create a new JWT access token with expiration.
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode, 
            self.secret_key, 
            algorithm=self.algorithm
        )
        return encoded_jwt
        
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode a JWT token and return the payload.
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthError("Invalid token")
```

### Password Handling

Password security is managed in `backend/shared/auth/password.py`:

- **Hashing**: Passwords are hashed using bcrypt with per-password salts
- **Verification**: Secure password comparison without timing attacks
- **Password Policy**: Enforces minimum complexity requirements

### Multi-Factor Authentication

The system supports optional two-factor authentication:

- Time-based One-Time Password (TOTP) implementation
- QR code generation for authenticator apps
- Backup codes for recovery

## Authorization

### Role-Based Access Control

The system implements role-based access control (RBAC) with the following roles:

- **Admin**: Full system access
- **Manager**: Access to management functions
- **User**: Basic access to scraping results
- **API**: Machine-to-machine access with limited permissions

### Permission System

Permissions are granular and can be assigned to both roles and individual users:

```python
class Permission(Enum):
    READ_LISTINGS = "read:listings"
    CREATE_LISTINGS = "create:listings"
    UPDATE_LISTINGS = "update:listings"
    DELETE_LISTINGS = "delete:listings"
    MANAGE_USERS = "manage:users"
    ADMIN_ACCESS = "admin:access"
```

### API Endpoint Protection

API endpoints are protected with middleware that verifies JWT tokens and checks permissions:

```python
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Public endpoints bypass auth checks
    if request.url.path in PUBLIC_ENDPOINTS:
        return await call_next(request)
    
    # Check for auth header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return JSONResponse(
            status_code=401,
            content={"detail": "Authorization header is missing"}
        )
    
    # Validate token
    try:
        token_type, token = auth_header.split()
        if token_type.lower() != "bearer":
            raise AuthError("Invalid token type")
            
        jwt_handler = JWTHandler(settings.SECRET_KEY)
        payload = jwt_handler.decode_token(token)
        
        # Add user info to request state
        request.state.user = payload
        
        # Check permissions for endpoint
        if not has_permission(payload, request.url.path, request.method):
            return JSONResponse(
                status_code=403,
                content={"detail": "Insufficient permissions"}
            )
            
        return await call_next(request)
    except Exception as e:
        return JSONResponse(
            status_code=401,
            content={"detail": str(e)}
        )
```

## API Security

### Rate Limiting

Rate limiting is implemented to prevent abuse and DoS attacks:

```python
class RateLimiter:
    def __init__(
        self, 
        redis_client: Redis, 
        limit: int = 100, 
        window: int = 3600,
        key_prefix: str = "rate_limit"
    ):
        self.redis = redis_client
        self.limit = limit
        self.window = window
        self.key_prefix = key_prefix
        
    async def is_rate_limited(self, key: str) -> Tuple[bool, int]:
        """
        Check if a key is rate limited.
        Returns (is_limited, remaining_requests).
        """
        redis_key = f"{self.key_prefix}:{key}"
        
        # Get current count
        count = await self.redis.get(redis_key)
        count = int(count) if count else 0
        
        if count >= self.limit:
            # Get TTL
            ttl = await self.redis.ttl(redis_key)
            return True, 0
            
        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incr(redis_key)
        
        # Set expiry if it's a new key
        if count == 0:
            pipe.expire(redis_key, self.window)
            
        await pipe.execute()
        
        return False, self.limit - count - 1
```

### Input Validation

All API inputs are validated using Pydantic models to prevent injection attacks:

```python
class ListingSearchParams(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    location: Optional[str] = None
    distance: Optional[int] = None
    
    @validator("query")
    def validate_query(cls, v):
        if v and len(v) > 200:
            raise ValueError("Query too long")
        return v
        
    @validator("min_price", "max_price")
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError("Price cannot be negative")
        return v
```

### CORS Configuration

Cross-Origin Resource Sharing (CORS) is configured to restrict access to trusted domains:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://marketplace-scraper.example.com",
        "https://admin.marketplace-scraper.example.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
```

## Data Protection

### Sensitive Data Handling

The system follows these practices for sensitive data:

1. **Minimization**: Only collects necessary data
2. **Encryption at Rest**: Database encryption for sensitive fields
3. **Encryption in Transit**: TLS for all connections
4. **Data Masking**: PII is masked in logs and reports

### Database Security

Database security measures include:

1. **Connection Encryption**: SSL/TLS for database connections
2. **Least Privilege**: Service accounts with minimal permissions
3. **Query Parametrization**: Prevention of SQL injection
4. **Connection Pooling**: Secure connection management

Example of secure database operations:

```python
async def get_user_by_email(email: str) -> Optional[User]:
    """
    Get a user by email with parameterized query.
    """
    query = """
    SELECT id, email, password_hash, role, is_active
    FROM users
    WHERE email = $1
    """
    
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(query, email)
        
        if not row:
            return None
            
        return User(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            role=row["role"],
            is_active=row["is_active"]
        )
```

## Network Security

### TLS Configuration

All services use TLS 1.3 with strong cipher suites:

```python
ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain(
    certfile="path/to/cert.pem",
    keyfile="path/to/key.pem"
)
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3
ssl_context.set_ciphers("HIGH:!aNULL:!eNULL:!MD5:!3DES")
```

### Network Policies

Kubernetes network policies restrict communication between services:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-service-policy
spec:
  podSelector:
    matchLabels:
      app: api-service
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-system
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: kafka
    ports:
    - protocol: TCP
      port: 9092
```

## Secrets Management

### Environment Variables

Sensitive configuration is managed via environment variables:

```bash
# Required
export SECRET_KEY="your-secure-secret-key"
export DATABASE_URL="postgresql://user:password@localhost/dbname"
export KAFKA_BOOTSTRAP_SERVERS="kafka:9092"

# Optional
export JWT_EXPIRE_MINUTES=30
export REDIS_URL="redis://localhost:6379/0"
```

### Kubernetes Secrets

In production, secrets are managed using Kubernetes Secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
type: Opaque
data:
  secret-key: base64-encoded-secret-key
  database-url: base64-encoded-database-url
  jwt-secret: base64-encoded-jwt-secret
```

## Audit Trail

### User Activity Logging

All security-relevant events are logged with the following information:

- Timestamp
- User ID
- IP address
- Action performed
- Resource affected
- Success/failure status

Example log format:

```json
{
  "timestamp": "2023-11-10T15:45:22.123Z",
  "level": "INFO",
  "logger": "security.audit",
  "user_id": "user-123",
  "ip": "192.168.1.100",
  "action": "LOGIN",
  "resource": "auth_system",
  "status": "SUCCESS",
  "details": {"auth_method": "password"}
}
```

### Log Security

Log security measures include:

1. **Centralized Logging**: All logs sent to secure log aggregation
2. **Immutability**: Logs cannot be modified once written
3. **Retention**: Logs kept for compliance purposes
4. **Access Control**: Restricted access to security logs

## Security Testing

### Automated Security Testing

The CI/CD pipeline includes:

1. **Static Analysis**: Code scanning for security vulnerabilities
2. **Dependency Scanning**: Checking for vulnerable dependencies
3. **Container Scanning**: Scanning Docker images for vulnerabilities
4. **Dynamic Testing**: API security testing with OWASP ZAP

### Penetration Testing

Regular penetration testing is performed focusing on:

1. Authentication and authorization
2. API security
3. Injection vulnerabilities
4. Infrastructure security

## Incident Response

### Security Incident Process

The security incident response process includes:

1. **Detection**: Monitoring systems detect anomalies
2. **Containment**: Isolate affected systems
3. **Investigation**: Analyze root cause
4. **Remediation**: Fix vulnerabilities
5. **Recovery**: Restore systems to normal operation
6. **Post-Incident**: Review and improve security measures

## Compliance

The system is designed to comply with:

- GDPR for data privacy
- OWASP Top 10 security best practices
- CIS Docker Benchmarks
- Relevant industry standards

## Security Hardening

### Container Security

Docker containers are hardened following best practices:

1. **Minimal Base Images**: Alpine-based images for small attack surface
2. **Non-Root Users**: Services run as non-privileged users
3. **Read-Only Filesystems**: When possible
4. **No Unnecessary Packages**: Minimize included software

Example Dockerfile with security best practices:

```dockerfile
FROM python:3.9-alpine

# Install dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Setup application
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set proper permissions
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Set read-only filesystem where possible
VOLUME ["/app/data"]

# Run the application
CMD ["python", "-m", "backend.services.api.src.main"]
```

### Regular Updates

Security updates are applied according to:

1. **Dependency Updates**: Weekly automated checks
2. **OS Patching**: Monthly or as critical updates are released
3. **Application Updates**: Continuous deployment with security fixes

## Best Practices for Developers

Security guidelines for developers working on the project:

1. **Secure Coding**: Follow OWASP secure coding guidelines
2. **Authentication**: Always use the provided authentication system
3. **Input Validation**: Validate all user inputs
4. **Error Handling**: Use secure error handling that doesn't leak information
5. **Dependency Management**: Only use approved dependencies

## Related Documentation

- [Architecture Overview](architecture.md)
- [Deployment Guide](deployment.md)
- [API Documentation](api.md)
- [Monitoring Documentation](monitoring.md)
