# MemeGPT API Documentation

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Endpoints](#endpoints)
  - [Authentication](#authentication-endpoints)
  - [Meme Generation](#meme-generation-endpoints)
  - [Job Management](#job-management-endpoints)
  - [User Management](#user-management-endpoints)
  - [Trending](#trending-endpoints)
  - [Billing](#billing-endpoints)
  - [Health](#health-endpoints)
- [WebSocket](#websocket)
- [Examples](#examples)

---

## Overview

MemeGPT API is a RESTful API built with FastAPI that enables AI-powered meme generation, user management, and billing integration. The API supports:

- **AI-Powered Meme Generation** using GPT-4o
- **Async Job Processing** with real-time status updates
- **User Authentication** with JWT tokens
- **Subscription Management** with Stripe integration
- **Rate Limiting** based on subscription tier
- **Image Storage** via Cloudflare R2

---

## Authentication

### JWT Token-Based Authentication

All protected endpoints require an `Authorization` header with a JWT bearer token.

#### Token Acquisition

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "password123"
  }'
```

#### Using the Token

```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Token Expiry

- **Access Token**: 60 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Refresh Token**: 7 days

#### Refresh Token

```bash
curl -X POST "http://localhost:8000/api/auth/refresh" \
  -H "Authorization: Bearer YOUR_REFRESH_TOKEN"
```

---

## Base URL

| Environment | URL |
|-------------|-----|
| Local Development | `http://localhost:8000` |
| Production | `https://api.memegpt.dev` |

---

## Error Handling

### Error Response Format

All errors follow this standard format:

```json
{
  "detail": "Error message",
  "status_code": 400,
  "error_code": "INVALID_REQUEST",
  "timestamp": "2024-04-20T10:30:00Z"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `200` | OK | Request successful |
| `201` | Created | Resource created successfully |
| `400` | Bad Request | Invalid request parameters |
| `401` | Unauthorized | Missing or invalid authentication |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource not found |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server error |

### Common Error Codes

| Code | Message | Solution |
|------|---------|----------|
| `INVALID_CREDENTIALS` | Invalid username or password | Check credentials |
| `TOKEN_EXPIRED` | JWT token has expired | Refresh token |
| `RATE_LIMIT_EXCEEDED` | Rate limit exceeded for your tier | Upgrade plan or wait |
| `INVALID_MEME_TEMPLATE` | Template not found | Use valid template ID |
| `PROCESSING_ERROR` | Failed to generate meme | Retry request |

---

## Rate Limiting

Rate limiting is applied per API key/user and subscription tier.

### Rate Limit Headers

Each response includes:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640195200
```

### Tier Limits

| Tier | Requests/Hour | Concurrent Jobs | Storage (GB) |
|------|---------------|-----------------|--------------|
| Free | 10 | 1 | 1 |
| Pro | 100 | 5 | 10 |
| Enterprise | Unlimited | Unlimited | Unlimited |

### Rate Limit Exceeded

```json
{
  "detail": "Rate limit exceeded. Limit: 10 requests/hour",
  "status_code": 429,
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 3600
}
```

---

## Endpoints

### Authentication Endpoints

#### 1. Register User

**POST** `/api/auth/register`

Create a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "secure_password_123"
}
```

**Response:** `201 Created`
```json
{
  "id": "usr_123",
  "email": "user@example.com",
  "username": "johndoe",
  "created_at": "2024-04-20T10:30:00Z",
  "tier": "free"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid email or weak password
- `409 Conflict` - User already exists

---

#### 2. Login User

**POST** `/api/auth/login`

Authenticate user and receive JWT token.

**Request Body:**
```json
{
  "username": "user@example.com",
  "password": "secure_password_123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "usr_123",
    "email": "user@example.com",
    "username": "johndoe",
    "tier": "pro"
  }
}
```

---

#### 3. Get Current User

**GET** `/api/auth/me`

Get authenticated user information.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "id": "usr_123",
  "email": "user@example.com",
  "username": "johndoe",
  "tier": "pro",
  "created_at": "2024-04-20T10:30:00Z",
  "last_login": "2024-04-20T15:45:00Z",
  "api_key": "sk_live_abc123def456..."
}
```

---

#### 4. Refresh Token

**POST** `/api/auth/refresh`

Refresh expired access token.

**Headers:**
```
Authorization: Bearer {refresh_token}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### Meme Generation Endpoints

#### 1. Generate Meme

**POST** `/api/memes/generate`

Create a new meme asynchronously.

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "prompt": "My code works but I don't know why",
  "template_id": "tpl_drake",
  "style": "classic",
  "custom_text": {
    "top": "When you find working code online",
    "bottom": "You don't question it"
  }
}
```

**Response:** `202 Accepted`
```json
{
  "job_id": "job_abc123",
  "status": "queued",
  "created_at": "2024-04-20T10:30:00Z",
  "estimated_wait": 5,
  "meme": {
    "id": "meme_xyz789",
    "url": null,
    "status": "processing"
  }
}
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `async` | boolean | No | Process asynchronously (default: true) |

---

#### 2. Get Meme

**GET** `/api/memes/{meme_id}`

Retrieve a specific meme by ID.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "id": "meme_xyz789",
  "user_id": "usr_123",
  "template_id": "tpl_drake",
  "text": {
    "top": "My code works but I don't know why",
    "bottom": "You don't question it"
  },
  "image_url": "https://cdn.memegpt.dev/memes/meme_xyz789.png",
  "likes": 42,
  "shares": 12,
  "created_at": "2024-04-20T10:30:00Z"
}
```

---

#### 3. List User Memes

**GET** `/api/memes/`

Get paginated list of user's created memes.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | 0 | Number of items to skip |
| `limit` | integer | 20 | Number of items to return (max: 100) |
| `sort` | string | created_desc | Sort order |

**Response:** `200 OK`
```json
{
  "total": 150,
  "skip": 0,
  "limit": 20,
  "items": [
    {
      "id": "meme_xyz789",
      "image_url": "https://cdn.memegpt.dev/memes/meme_xyz789.png",
      "created_at": "2024-04-20T10:30:00Z",
      "likes": 42
    }
  ]
}
```

---

#### 4. Delete Meme

**DELETE** `/api/memes/{meme_id}`

Delete a meme created by the user.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:** `204 No Content`

**Error Responses:**
- `404 Not Found` - Meme not found
- `403 Forbidden` - User doesn't own this meme

---

#### 5. List Available Templates

**GET** `/api/memes/templates`

Get list of available meme templates.

**Response:** `200 OK`
```json
{
  "total": 42,
  "templates": [
    {
      "id": "tpl_drake",
      "name": "Drake Hotline Bling",
      "description": "Drake saying no to one thing, yes to another",
      "image_url": "https://cdn.memegpt.dev/templates/drake.jpg",
      "category": "reaction",
      "text_fields": 2,
      "popularity": 95
    }
  ]
}
```

---

### Job Management Endpoints

#### 1. Get Job Status

**GET** `/api/jobs/{job_id}`

Get status of an async job.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "id": "job_abc123",
  "status": "completed",
  "progress": 100,
  "result": {
    "meme_id": "meme_xyz789",
    "image_url": "https://cdn.memegpt.dev/memes/meme_xyz789.png"
  },
  "created_at": "2024-04-20T10:30:00Z",
  "completed_at": "2024-04-20T10:35:00Z"
}
```

**Job Status Values:**
- `queued` - Waiting to be processed
- `processing` - Currently being processed
- `completed` - Job finished successfully
- `failed` - Job failed with error

---

#### 2. Cancel Job

**POST** `/api/jobs/{job_id}/cancel`

Cancel a pending or processing job.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "id": "job_abc123",
  "status": "cancelled",
  "cancelled_at": "2024-04-20T10:32:00Z"
}
```

---

### User Management Endpoints

#### 1. Update User Profile

**PUT** `/api/auth/users/profile`

Update user information.

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "johndoe_new",
  "email": "newemail@example.com",
  "bio": "Meme enthusiast"
}
```

**Response:** `200 OK`
```json
{
  "id": "usr_123",
  "email": "newemail@example.com",
  "username": "johndoe_new",
  "bio": "Meme enthusiast",
  "updated_at": "2024-04-20T10:30:00Z"
}
```

---

#### 2. Change Password

**POST** `/api/auth/users/change-password`

Change user password.

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "current_password": "old_password_123",
  "new_password": "new_secure_password_456"
}
```

**Response:** `200 OK`
```json
{
  "message": "Password changed successfully"
}
```

---

#### 3. Generate API Key

**POST** `/api/auth/users/api-key`

Generate new API key for programmatic access.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:** `201 Created`
```json
{
  "api_key": "sk_live_abc123def456ghi789",
  "created_at": "2024-04-20T10:30:00Z",
  "last_used": null
}
```

---

### Trending Endpoints

#### 1. Get Trending Memes

**GET** `/api/trending`

Get trending memes across the platform.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 20 | Number of items to return |
| `timeframe` | string | 24h | Trending timeframe (1h, 24h, 7d) |
| `category` | string | all | Filter by category |

**Response:** `200 OK`
```json
{
  "timeframe": "24h",
  "total": 1250,
  "memes": [
    {
      "id": "meme_abc123",
      "user": {
        "id": "usr_456",
        "username": "meme_lord"
      },
      "image_url": "https://cdn.memegpt.dev/memes/meme_abc123.png",
      "likes": 2450,
      "shares": 890,
      "views": 45000,
      "created_at": "2024-04-20T08:00:00Z"
    }
  ]
}
```

---

### Billing Endpoints

#### 1. Get Subscription

**GET** `/api/stripe/subscription`

Get current subscription information.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "id": "sub_123",
  "status": "active",
  "tier": "pro",
  "current_period_start": "2024-04-01T00:00:00Z",
  "current_period_end": "2024-05-01T00:00:00Z",
  "cancel_at_period_end": false,
  "price": 9.99,
  "currency": "usd",
  "features": {
    "requests_per_hour": 100,
    "concurrent_jobs": 5,
    "storage_gb": 10
  }
}
```

---

#### 2. Create Checkout Session

**POST** `/api/stripe/checkout`

Create Stripe checkout session for plan upgrade.

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "plan_id": "plan_pro",
  "success_url": "https://yourdomain.com/billing/success",
  "cancel_url": "https://yourdomain.com/billing/cancel"
}
```

**Response:** `200 OK`
```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_test_abc123def456ghi789",
  "session_id": "cs_test_abc123def456ghi789"
}
```

---

#### 3. Webhook Handler

**POST** `/api/stripe/webhook`

Handle Stripe webhooks for subscription events.

**Headers:**
```
Stripe-Signature: {signature}
Content-Type: application/json
```

**Handled Events:**
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`

---

### Health Endpoints

#### 1. Health Check

**GET** `/api/health`

Get API health status.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2024-04-20T10:30:00Z",
  "services": {
    "database": "connected",
    "redis": "connected",
    "openai": "connected"
  }
}
```

---

#### 2. Readiness Check

**GET** `/api/ready`

Check if API is ready to accept requests.

**Response:** `200 OK`
```json
{
  "ready": true,
  "timestamp": "2024-04-20T10:30:00Z"
}
```

---

## WebSocket

### Real-Time Job Progress

Connect to WebSocket for real-time job progress updates.

**URL:** `ws://localhost:8000/ws/jobs/{job_id}`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Message Format:**

```json
{
  "type": "progress",
  "job_id": "job_abc123",
  "status": "processing",
  "progress": 50,
  "message": "Generating image..."
}
```

**Python Example:**
```python
import asyncio
import websockets
import json

async def connect_to_job():
    uri = "ws://localhost:8000/ws/jobs/job_abc123"
    headers = {"Authorization": "Bearer YOUR_TOKEN"}
    
    async with websockets.connect(uri, extra_headers=headers) as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Progress: {data['progress']}%")
            
            if data['status'] == 'completed':
                break

asyncio.run(connect_to_job())
```

---

## Examples

### Example 1: Generate Meme (JavaScript/Node.js)

```javascript
const API_URL = 'http://localhost:8000';
let authToken = null;

// 1. Login
async function login() {
  const response = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: 'user@example.com',
      password: 'password123'
    })
  });
  
  const data = await response.json();
  authToken = data.access_token;
  return authToken;
}

// 2. Generate Meme
async function generateMeme(prompt) {
  const response = await fetch(`${API_URL}/api/memes/generate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      prompt: prompt,
      template_id: 'tpl_drake'
    })
  });
  
  const data = await response.json();
  return data.job_id;
}

// 3. Check Job Status
async function checkJobStatus(jobId) {
  const response = await fetch(`${API_URL}/api/jobs/${jobId}`, {
    headers: { 'Authorization': `Bearer ${authToken}` }
  });
  
  return await response.json();
}

// 4. Main Flow
async function main() {
  await login();
  const jobId = await generateMeme('My code works but I don\'t know why');
  
  let completed = false;
  while (!completed) {
    const status = await checkJobStatus(jobId);
    console.log(`Status: ${status.status}`);
    
    if (status.status === 'completed') {
      console.log(`Meme URL: ${status.result.image_url}`);
      completed = true;
    } else if (status.status === 'failed') {
      console.error('Generation failed:', status.error);
      completed = true;
    }
    
    await new Promise(r => setTimeout(r, 1000));
  }
}

main();
```

### Example 2: Generate Meme (Python)

```python
import requests
import time
from typing import Optional

class MemeGPTClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token: Optional[str] = None
    
    def login(self, username: str, password: str) -> str:
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        self.token = response.json()["access_token"]
        return self.token
    
    def generate_meme(self, prompt: str, template_id: str = "tpl_drake") -> str:
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.post(
            f"{self.base_url}/api/memes/generate",
            json={"prompt": prompt, "template_id": template_id},
            headers=headers
        )
        response.raise_for_status()
        return response.json()["job_id"]
    
    def get_job_status(self, job_id: str) -> dict:
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/api/jobs/{job_id}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    def wait_for_completion(self, job_id: str, timeout: int = 60) -> dict:
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_job_status(job_id)
            
            if status["status"] == "completed":
                return status["result"]
            elif status["status"] == "failed":
                raise Exception(f"Job failed: {status.get('error')}")
            
            time.sleep(1)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")

# Usage
client = MemeGPTClient()
client.login("user@example.com", "password123")
job_id = client.generate_meme("My code works but I don't know why")
result = client.wait_for_completion(job_id)
print(f"Generated meme: {result['image_url']}")
```

### Example 3: Using cURL

```bash
# 1. Login
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "password123"
  }' > auth.json

# Extract token
TOKEN=$(jq -r '.access_token' auth.json)

# 2. Generate meme
curl -X POST "http://localhost:8000/api/memes/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "My code works but I don\''t know why",
    "template_id": "tpl_drake"
  }' > job.json

# Extract job ID
JOB_ID=$(jq -r '.job_id' job.json)

# 3. Poll for completion
for i in {1..30}; do
  curl -X GET "http://localhost:8000/api/jobs/$JOB_ID" \
    -H "Authorization: Bearer $TOKEN" > status.json
  
  STATUS=$(jq -r '.status' status.json)
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "completed" ]; then
    jq '.result' status.json
    break
  fi
  
  sleep 2
done
```

---

## Rate Limit Best Practices

1. **Implement Exponential Backoff**: When receiving 429 status, wait before retrying
2. **Check Rate Limit Headers**: Use `X-RateLimit-Remaining` to plan requests
3. **Cache Results**: Store successful responses to avoid redundant API calls
4. **Batch Operations**: Combine multiple requests into single operations when possible

---

## Support & Feedback

For API issues or feature requests:
- 📧 Email: api-support@memegpt.dev
- 🐛 GitHub Issues: [Report a bug](https://github.com/your-repo/MemeGPT/issues)
- 💬 Discord: [Join community](https://discord.gg/memegpt)

---

**Last Updated**: April 20, 2024
**API Version**: 2.0.0
