---
name: api-discovery
description: Comprehensive API discovery through network analysis, mobile decompilation, and documentation generation. Use for finding hidden APIs, understanding authentication flows, and mapping endpoints.
---

## API Discovery Skill

### When to Activate
- User mentions: "cari API", "reverse engineer", "sniff network", "analyze app"
- Task involves: Undocumented APIs, mobile app analysis, web scraping
- Keywords detected: "API key", "endpoint", "authentication", "payload"

### Resources
- @network-analysis.md - Traffic capture techniques
- @mobile-decompilation.md - Mobile app analysis (ethical only)
- @api-documentation-template.md - Standard documentation format

### Execution Protocol

#### Phase 1: Target Assessment
1. **Identify platform**: Web, iOS, Android, Desktop API
2. **Legal check**: Confirm ethical boundaries
3. **Tool selection**: Playwright, mitmproxy, APKTool (for owned apps)

#### Phase 2: Reconnaissance
**For Web Apps**:
- Configure Playwright with HAR recording
- Execute complete user flows
- Capture all network traffic
- Analyze authentication patterns

**For Mobile Apps** (your own apps only):
- Decompile APK/IPA
- Extract API endpoints from strings
- Analyze network security config
- Proxy traffic through controlled environment

#### Phase 3: Analysis
1. **Extract patterns**:
   - Base URLs and versioning
   - Authentication methods (Bearer, OAuth, API Key)
   - Request/response schemas
   - Rate limiting indicators

2. **Document endpoints**:
   ```markdown
   ### POST /api/v1/auth/login
   - **Source**: Network sniffing
   - **Auth**: None (returns token)
   - **Request**: `{username, password, deviceId}`
   - **Response**: `{token, refreshToken, expiresIn}`
   - **Rate Limit**: 5 attempts/minute
   ```

#### Phase 4: Integration
1. Create adapter in `/integrations/`
2. Implement retry logic and error handling
3. Write tests validating discovered endpoints
4. Document integration pattern

### Output Artifacts
- `/docs/discovered-apis/[target]/openapi.yaml`
- `/docs/discovered-apis/[target]/endpoints.md`
- `/integrations/adapters/[target].ts`
- `/tests/integration/[target].test.ts`

### Safety Checkpoints
- [ ] Ethical review passed
- [ ] No credential exposure in logs
- [ ] Rate limiting respected
- [ ] Test environment isolated