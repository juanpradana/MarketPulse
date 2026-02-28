name: "API Reverse Engineering"
description: "Discover and document APIs from applications through network analysis"
trigger: ["cari API", "reverse engineer", "sniff", "analyze app", "API discovery"]

phases:
  1_reconnaissance:
    name: "Target Analysis"
    steps:
      - "Identify target platform (web/mobile/desktop)"
      - "Verify ethical/legal boundaries"
      - "Select appropriate tools (Playwright, mitmproxy)"
      - "Setup isolated test environment"
    checkpoint: "Target confirmed, tools ready, ethical check passed"

  2_capture:
    name: "Traffic Capture"
    steps:
      - "Configure Playwright with HAR recording"
      - "Execute complete user flows"
      - "Capture authentication flows"
      - "Record error scenarios"
      - "Export HAR file for analysis"
    checkpoint: "Comprehensive traffic captured"

  3_analysis:
    name: "Endpoint Extraction"
    steps:
      - "Parse HAR file for API calls"
      - "Identify base URLs and patterns"
      - "Extract authentication mechanisms"
      - "Document request/response schemas"
      - "Map rate limiting and error codes"
    checkpoint: "All endpoints documented"

  4_integration:
    name: "Adapter Development"
    steps:
      - "Create service adapter"
      - "Implement authentication handling"
      - "Add retry logic and error handling"
      - "Write integration tests"
      - "Document usage patterns"
    checkpoint: "Adapter functional, tests passing"

  5_validation:
    name: "Verification"
    steps:
      - "Replay discovered endpoints"
      - "Test authentication refresh"
      - "Verify error handling"
      - "Check rate limit compliance"
      - "Document limitations"
    checkpoint: "Integration validated, documented"

safety_checks:
  - "No credential exposure in logs"
  - "Rate limits respected"
  - "Test environment isolated"
  - "Documentation includes ethical notice"