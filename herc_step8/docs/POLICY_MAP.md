# Policy Enforcement Map

## Overview
This document maps each policy from POLICY_ADDENDUM.md to its enforcement location in the codebase.

## Security Policies

### 1.1 Network Binding (127.0.0.1 only)
| Component | File | Line/Function | Implementation |
|-----------|------|---------------|----------------|
| TN3270 Bridge API | `~/herc/bridge/tn3270_bridge/api.py` | `main()` | `uvicorn.run(host="127.0.0.1")` |
| Agent Controller | `~/herc/ai/agent_controller.py` | `__init__()` | `bridge_url="http://127.0.0.1:8080"` |
| Watchdog | `~/herc/tools/watchdog.py` | `HEALTH_URL` | `"http://127.0.0.1:8080/healthz"` |

### 1.2 Credential Redaction
| Component | File | Function | Implementation |
|-----------|------|----------|----------------|
| Logger | `~/herc/ai/agent_controller.py` | `redact_params()` | Redacts sensitive keys |
| JSONL Logger | `~/herc/ai/observability.py` | `log_action()` | Filters credential fields |
| Status Reporter | `~/herc/ai/agent_controller.py` | `update()` | Sanitizes status updates |

### 1.3 Action Allowlist
| Component | File | Function | Implementation |
|-----------|------|----------|----------------|
| Bridge API | `~/herc/bridge/tn3270_bridge/session.py` | `validate_action()` | Checks against ALLOWED_ACTIONS |
| Agent | `~/herc/ai/safety.py` | `is_allowed_action()` | Validates before execution |
| Dry-Run Mode | `~/herc/ai/agent_controller.py` | `_process_command()` | Validates without executing |

## Operational Policies

### 2.1 Retry and Timeout Limits
| Component | File | Function | Values |
|-----------|------|----------|--------|
| Connection | `~/herc/ai/tn3270_client.py` | `connect_with_retry()` | 3 attempts, 2/4/8s backoff |
| Actions | `~/herc/bridge/tn3270_bridge/session.py` | `execute()` | 30s timeout |
| Keyboard Lock | `~/herc/ai/agent_controller.py` | `handle_keyboard_lock()` | 3 recovery attempts |

### 2.2 Logging and Observability
| Component | File | Location | Format |
|-----------|------|----------|--------|
| Action Logs | `~/herc/ai/observability.py` | `~/herc/logs/ai/*.jsonl` | JSONL |
| Trace Logs | `~/herc/ai/agent_controller.py` | `~/herc/logs/ai/trace/` | Screen snapshots |
| Metrics | `~/herc/ai/metrics.py` | `~/herc/logs/ai/metrics.json` | Aggregated JSON |

### 2.3 Error Recovery
| Component | File | Function | Strategy |
|-----------|------|----------|----------|
| Session Recovery | `~/herc/bridge/tn3270_bridge/api.py` | `/reset_session` | Disconnect + reconnect |
| Keyboard Recovery | `~/herc/ai/agent_controller.py` | `recover_keyboard()` | PF3 → Clear → Reset |
| Fallback Logic | `~/herc/tools/flow_runner.py` | `handle_error()` | Flow-based recovery |

## Governance Policies

### 3.1 Execution Modes
| Mode | File | Function | Behavior |
|------|------|----------|----------|
| Interactive | `~/herc/ai/run_agent.py` | `--interactive` | Command queue monitoring |
| Batch | `~/herc/ai/run_agent.py` | `--batch` | Single goal execution |
| Dry-Run | `~/herc/ai/run_agent.py` | `--dry-run` | Planning only |
| Confirm | `~/herc/ai/run_agent.py` | `--confirm` | User approval required |

### 3.2 Resource Limits
| Limit | File | Location | Value |
|-------|------|----------|-------|
| Max Steps | `~/herc/config.yaml` | `limits.max_steps` | 40 |
| Max Time | `~/herc/config.yaml` | `limits.max_time` | 600s |
| Prompt Budget | `~/herc/ai/llm_cli.py` | `MAX_TOKENS` | 4000 |

### 3.3 Audit and Compliance
| Component | File | Function | Purpose |
|-----------|------|----------|---------|
| Action Logger | `~/herc/ai/observability.py` | `log_action()` | Audit trail |
| Replay Harness | `~/herc/tools/replay_harness.py` | `replay()` | Regression testing |
| Evaluator | `~/herc/tools/evaluate.py` | `run_evaluation()` | Performance metrics |

## Development Policies

### 4.1 Configuration Management
| Config | File | Purpose |
|--------|------|---------|
| Main Config | `~/herc/config.yaml` | Central configuration |
| Flow Definitions | `~/herc/flows/*.yaml` | Automation sequences |
| Golden Screens | `~/herc/goldens/*.json` | Regression baselines |

### 4.2 Health and Monitoring
| Component | File | Endpoint/Function | Purpose |
|-----------|------|------------------|---------|
| Health Check | `~/herc/bridge/tn3270_bridge/api.py` | `/healthz` | System status |
| Watchdog | `~/herc/tools/watchdog.py` | `monitor()` | Auto-recovery |
| Metrics | `~/herc/ai/metrics.py` | `update_metrics()` | Performance tracking |

## Policy Updates
- **Last Updated**: 2024-01-01
- **Version**: 1.0.0
- **Next Review**: 2024-04-01

## Validation Commands
```bash
# Verify localhost binding
netstat -tlnp | grep 8080

# Check log redaction
grep -i password ~/herc/logs/ai/*.jsonl

# Validate action allowlist
python ~/herc/tools/validate_policies.py

# Run regression tests
python ~/herc/tools/replay_harness.py --golden
```