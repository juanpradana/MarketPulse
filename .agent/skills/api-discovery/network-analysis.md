# Network Analysis Guide

## Playwright HAR Recording

### Setup
```javascript
const context = await browser.newContext({
  recordHar: {
    path: 'analysis/traffic.har',
    mode: 'full'
  }
});
```

### Execution
1. Navigate to target URL
2. Perform complete user flows:
   - Authentication
   - CRUD operations
   - Search and filter
   - File uploads
3. Close context to save HAR

### Analysis
Parse HAR file for:
- Request URLs and methods
- Headers (authentication, content-type)
- Query parameters
- Request/response bodies
- Timing information

## mitmproxy Setup

### Installation
```bash
pip install mitmproxy
```

### Running
```bash
mitmproxy --mode regular --showhost
# or
mitmweb --mode regular --showhost
```

### SSL Pinning Bypass (for owned apps)
Configure device to trust mitmproxy CA certificate.

## Chrome DevTools

### Network Tab
- Preserve log across navigation
- Disable cache
- Throttle to simulate mobile networks
- Export HAR for analysis

### Key Filters
- `domain:api.example.com` - Filter by domain
- `method:POST` - Filter by method
- `has-response-header:content-type` - Find API calls