# Mainframe Automation Policy Addendum

## Overview
This document defines the security, operational, and governance policies for the mainframe automation system. These policies are enforced throughout the codebase and must be followed for all operations.

## 1. Security Policies

### 1.1 Network Binding
- **Policy**: All services MUST bind to localhost (127.0.0.1) only
- **Rationale**: Prevent external network exposure
- **Enforcement**: Hard-coded in service configurations

### 1.2 Credential Management
- **Policy**: Credentials MUST be:
  - Stored in environment variables or config files (never in code)
  - Redacted in all logs and outputs
  - Never transmitted over network
- **Redaction Keys**: `["pwd", "pass", "password", "pin", "secret", "key", "token"]`
- **Default Credentials**: HERC02/CUL8TR (demo only)

### 1.3 Action Allowlist
- **Policy**: Only approved s3270 actions may be executed
- **Allowed Actions**:
  ```
  Wait(3270)
  Wait(InputField)
  Ascii()
  ReadBuffer(Ascii)
  Query(...)
  MoveCursor(row,col)
  String("...")
  Enter
  PF(1-12)
  PA(1-3)
  Clear
  Disconnect()
  Connect(127.0.0.1:3270)
  ```
- **Denied**: Any filesystem operations, network calls, shell commands

## 2. Operational Policies

### 2.1 Retry and Timeout Limits
- **Connection Retry**: Max 3 attempts with exponential backoff (2s, 4s, 8s)
- **Action Timeout**: 30 seconds per action
- **Session Timeout**: 5 minutes of inactivity
- **Keyboard Lock Recovery**: Max 3 attempts (PF3, Clear, Disconnect)

### 2.2 Logging and Observability
- **Format**: JSONL (JSON Lines) for structured logging
- **Location**: `~/herc/logs/ai/`
- **Rotation**: Daily, max 7 days retention
- **Trace Mode**: Optional full screen captures in `~/herc/logs/ai/trace/`
- **Metrics**: Aggregated in `~/herc/logs/ai/metrics.json`

### 2.3 Error Recovery
- **Fallback Order**:
  1. Wait and retry (for transient errors)
  2. Send recovery keys (PF3, Clear)
  3. Reset session
  4. Full restart with snapshot
- **Max Fallbacks**: 2 per goal
- **No-Progress Detection**: Abort after 3 identical screens

## 3. Governance Policies

### 3.1 Execution Modes
- **Interactive**: Human in the loop with command queue
- **Batch**: Automated with defined goals
- **Dry-Run**: Planning only, no execution
- **Confirm**: Require user approval per action

### 3.2 Resource Limits
- **Max Steps per Goal**: 40 actions
- **Max Execution Time**: 10 minutes per goal
- **Prompt Budget**: 4000 tokens per request
- **Screen Truncation**: 24x80 characters max

### 3.3 Audit and Compliance
- **Action Logging**: Every action logged with timestamp and outcome
- **Session Recording**: Optional transcript recording for replay
- **Golden Screens**: Baseline snapshots for regression testing
- **Evaluation Metrics**: Success rate, action count, latency

## 4. Development Policies

### 4.1 Code Standards
- **Language**: Python 3.8+
- **Dependencies**: Minimal, vendored when possible
- **Testing**: Unit tests for critical paths
- **Documentation**: Inline comments and README files

### 4.2 Change Management
- **Policy Updates**: Require review and POLICY_MAP.md update
- **Flow Changes**: Test with replay harness before deployment
- **Configuration**: Version controlled in config.yaml

### 4.3 Demo Safety
- **Demo Mode**: Use test credentials only
- **Data Isolation**: No production data access
- **Rollback**: Snapshot before demo, restore after

## 5. Compliance Verification

### 5.1 Health Checks
- **Endpoint**: `/healthz` - system status
- **Watchdog**: Auto-restart on failure
- **Monitoring**: Metrics dashboard

### 5.2 Regression Testing
- **Replay Harness**: Test flows against golden screens
- **Evaluation Suite**: 3 standard scenarios
- **Success Criteria**: ≥95% success rate

### 5.3 Security Scanning
- **No Secrets**: Scan for hardcoded credentials
- **No External Calls**: Verify localhost-only
- **Action Validation**: Confirm allowlist enforcement

## Policy Version
- **Version**: 1.0.0
- **Date**: 2024-01-01
- **Author**: System Administrator
- **Review**: Quarterly

## Enforcement
See POLICY_MAP.md for implementation details and code locations where each policy is enforced.