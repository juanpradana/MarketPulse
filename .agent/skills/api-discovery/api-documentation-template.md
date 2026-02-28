# API Documentation Template

## Service Information
- **Name**: [Service Name]
- **Base URL**: https://api.example.com
- **Version**: v1
- **Documentation Source**: [Network analysis / Public docs / Reverse engineering]
- **Last Updated**: [Date]
- **Analyst**: [Name]

## Authentication

### Method: [OAuth 2.0 / API Key / Bearer Token / None]

#### OAuth 2.0 Flow
1. Authorization endpoint: `GET /oauth/authorize`
2. Token endpoint: `POST /oauth/token`
3. Refresh endpoint: `POST /oauth/refresh`

#### API Key
- Header: `X-API-Key: your_key_here`
- Query param: `?api_key=your_key_here`

## Rate Limiting
- **Limit**: 1000 requests/hour
- **Headers**:
  - `X-RateLimit-Limit`: 1000
  - `X-RateLimit-Remaining`: 999
  - `X-RateLimit-Reset`: 1640000000

## Endpoints

### [Method] /path/to/endpoint

**Description**: Brief description of what this endpoint does.

**Authentication**: Required / Optional

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| param1 | string | Yes | Description |
| param2 | integer | No | Description |

**Request Example**:
```json
{
  "param1": "value",
  "param2": 123
}
```

**Response Example** (200 OK):
```json
{
  "id": "uuid",
  "status": "success",
  "data": { ... }
}
```

**Error Responses**:

| Status | Code | Description |
|--------|------|-------------|
| 400 | INVALID_REQUEST | Missing required parameter |
| 401 | UNAUTHORIZED | Invalid or expired token |
| 429 | RATE_LIMITED | Too many requests |

**Notes**:
- Special considerations
- Known limitations
- Changelog