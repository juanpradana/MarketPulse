name: "Cross-Platform Integration"
description: "Integrate multiple applications and services into cohesive system"
trigger: ["integrate systems", "connect services", "sync platforms", "bridge apps"]

phases:
  1_discovery:
    name: "Service Discovery"
    steps:
      - "Map all services to integrate"
      - "Document APIs, protocols, data formats"
      - "Identify authentication methods"
      - "Check rate limits and SLAs"
    checkpoint: "All services mapped and documented"

  2_contract:
    name: "Contract Definition"
    steps:
      - "Define data models and transformations"
      - "Create OpenAPI specs for new endpoints"
      - "Establish event schemas"
      - "Document error handling"
    checkpoint: "Contracts agreed, schemas defined"

  3_adapter:
    name: "Adapter Implementation"
    steps:
      - "Build service adapters"
      - "Implement circuit breakers"
      - "Add monitoring and logging"
      - "Create retry mechanisms"
    checkpoint: "Adapters tested individually"

  4_orchestration:
    name: "Workflow Orchestration"
    steps:
      - "Implement saga pattern for transactions"
      - "Setup event bus or message queue"
      - "Create compensation logic"
      - "Add distributed tracing"
    checkpoint: "Workflows tested end-to-end"

  5_sync:
    name: "Data Synchronization"
    steps:
      - "Implement initial data migration"
      - "Setup real-time sync"
      - "Handle conflict resolution"
      - "Create reconciliation jobs"
    checkpoint: "Data consistent across platforms"

  6_monitoring:
    name: "Monitoring & Alerting"
    steps:
      - "Setup metrics collection"
      - "Configure alerts"
      - "Create dashboards"
      - "Document runbooks"
    checkpoint: "Production ready, monitored"

error_recovery:
  service_down:
    action: "circuit_breaker_open"
    fallback: "degraded_mode"
    
  data_conflict:
    action: "manual_resolution_queue"
    notify: "data_team"
    
  sync_failure:
    action: "retry_with_backoff"
    max_retries: 5