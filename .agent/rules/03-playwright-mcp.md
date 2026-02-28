---
name: playwright-mcp
description: Browser automation for testing, scraping, and verification
glob: "**/*"
alwaysApply: true
trigger: always_on
---

# Playwright MCP Protocol v2.0

## Core Principle: Snapshot-Driven Automation
Your "eyes" are `browser_snapshot` - structured accessibility trees, not screenshots.
**NEVER** use screenshots for automation decisions.

## The SIA Loop (Snapshot → Identify → Act)

1. **SNAPSHOT**: `browser_snapshot` for current state
2. **IDENTIFY**: Parse for element `ref` IDs and accessibility info
3. **ACT**: Execute with `ref` + human-readable description
4. **VERIFY**: New snapshot to confirm state change

## Tool Categories

### Navigation & State
- `browser_navigate` - Load URL (first step)
- `browser_snapshot` - **PRIMARY TOOL** for state awareness
- `browser_navigate_back` - History navigation
- `browser_close` - Cleanup

### Interaction (Require `ref` from snapshot)
- `browser_click` - Element activation
- `browser_type` - Text input
- `browser_fill_form` - Batch form completion
- `browser_select_option` - Dropdown selection
- `browser_hover` - Mouse hover states
- `browser_drag` - Drag and drop
- `browser_press_key` - Keyboard input
- `browser_file_upload` - File selection

### Verification & Debug
- `browser_take_screenshot` - **VISUAL OUTPUT ONLY** (not for automation)
- `browser_console_messages` - Error detection
- `browser_network_requests` - API call monitoring
- `browser_wait_for` - Timing control

## Execution Modes

### Mode 1: Test Generation (Default)
**NEVER** write tests from scenarios alone. **ALWAYS**:
1. Execute steps manually via MCP tools
2. Verify each step with snapshots
3. Generate test code from verified steps
4. Use @playwright/test with:
   - Page Object Model (classes for locators)
   - Web-first assertions (`toBeVisible`, `toHaveText`)
   - Avoid `page.locator`, use `getByRole`, `getByLabel`
   - No hardcoded timeouts

### Mode 2: Network Analysis (Reverse Engineering)
For API discovery:
1. Configure `browser_context` with `recordHar: true`
2. Execute user flows completely
3. Analyze HAR file for:
   - Endpoint patterns
   - Authentication methods
   - Payload structures
   - Response formats

### Mode 3: Visual Regression
1. Screenshots at key breakpoints
2. Compare with baselines
3. Responsive testing across viewports

## Integration with Sequential Thinking

- **Thought 1-3**: Plan exploration path
- **Thought 4**: Initial navigation
- **Thought 5+**: Execute SIA loop, document findings
- **Final Thought**: Generate test code or analysis report

## Network Analysis for Reverse Engineering

```javascript
// Configuration for API discovery
{
  "recordHar": true,
  "harPath": "./analysis/[app-name].har",
  "bypassCSP": true,
  "extraHTTPHeaders": {
    "Accept": "application/json"
  }
}
```

Extract and document:
- Base URLs and path patterns
- Authentication headers/tokens
- Request/response schemas
- Rate limiting indicators
- Error response formats

## Safety Protocols

- **NEVER** execute destructive actions on production without confirmation
- **ALWAYS** validate selectors before batch operations
- **VERIFY** page state before and after actions
- **CLEANUP** browser instances after use