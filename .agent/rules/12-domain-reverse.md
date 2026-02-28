---
name: domain-reverse
description: Reverse engineering protocols for API discovery and analysis
glob: "reverse-engineer/**/*.{ts,js,py,md}"
alwaysApply: false
trigger: always_on
---

# Reverse Engineering Domain Standards

## Ethical & Legal Boundaries

### Permitted Activities
- **Public API documentation** analysis
- **Your own applications** inspection
- **Open source software** study
- **Educational purposes** with proper attribution

### Prohibited Activities
- **Bypassing authentication** or payment systems
- **Unauthorized data access** or extraction
- **Circumventing DRM** or licensing
- **Violating Terms of Service**

**Rule**: When in doubt, ask for explicit permission.

## Methodology: The SHERLOCK Protocol

**S**urveil - Observe system behavior
**H**arvest - Collect network traffic and artifacts
**E**xtract - Decode and parse data
**R**econstruct - Build API documentation
**L**everage - Create integration code
**O**rganize - Document findings
**C**heck - Validate and verify
**K**eep - Store securely with access controls

## Phase 1: Reconnaissance

### Target Analysis
- **Platform**: Web app, mobile app, desktop app, API
- **Tech stack**: Framework detection, build tools
- **Protection**: WAF, rate limiting, bot detection
- **Documentation**: Public docs, SDKs, changelogs

### Tool Selection
- **Web**: Chrome DevTools, Playwright MCP, mitmproxy
- **Mobile**: APKTool, JADX, Frida (for your own apps)
- **Desktop**: Proxyman, Charles Proxy, Wireshark
- **Network**: curl, httpie, Postman, Playwright HAR

## Phase 2: Traffic Analysis

### Web Application
1. **Playwright HAR recording**:
   ```javascript
   await context.routeFromHAR('analysis/app.har', {
     update: true,
     updateContent: 'embed'
   });
   ```

2. **Network pattern identification**:
   - Base URL patterns
   - Authentication mechanisms (Bearer, Cookie, API Key)
   - Request signatures (timestamps, nonces, signatures)
   - Rate limiting headers

3. **Endpoint mapping**:
   - REST patterns: GET /api/v1/users
   - GraphQL: /graphql with introspection
   - WebSocket: wss://realtime.example.com

### Mobile Application
1. **Static analysis** (APK/IPA):
   - Extract with APKTool
   - Decompile with JADX
   - Search for API endpoints in strings
   - Analyze network security config

2. **Dynamic analysis**:
   - Proxy traffic through mitmproxy
   - SSL pinning bypass (for your own apps)
   - Runtime memory analysis

## Phase 3: Documentation

### API Specification Template
```markdown
### Endpoint: [METHOD] /path
- **Source**: [Network sniffing / Decompilation / Public docs]
- **Authentication**: [None / API Key / Bearer / OAuth]
- **Rate Limit**: [X requests per Y minutes]
- **Request**:
  ```json
  {
    "field": "type // description"
  }
  ```
- **Response**:
  ```json
  {
    "field": "type // description"
  }
  ```
- **Error Codes**:
  - 400: Invalid request
  - 401: Unauthorized
  - 429: Rate limited
- **Notes**: [Special considerations]
```

## Phase 4: Integration

### Adapter Pattern
Create wrapper classes that:
- Normalize different API styles
- Handle authentication refresh
- Implement retry logic with backoff
- Transform data to internal models

### Testing
- **Replay**: Replicate discovered requests
- **Fuzzing**: Test edge cases and error handling
- **Monitoring**: Track for API changes

## Documentation Structure
```
docs/reverse-engineering/
├── [target-name]/
│   ├── openapi.yaml          # Generated spec
│   ├── endpoints.md          # Detailed documentation
│   ├── authentication.md     # Auth flow analysis
│   └── integration/
│       ├── adapter.ts        # Integration code
│       └── tests/
└── discoveries/              # Ongoing findings
```

## Integration with Playwright MCP

Use Playwright for:
- Automated traffic capture
- Session persistence analysis
- Form submission tracking
- WebSocket message logging
- HAR file generation and analysis