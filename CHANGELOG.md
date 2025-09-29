# Changelog

All notable changes to the Mainframe Copilot project are documented here.

## [1.1.0] - 2025-09-28

### Fixed
- **Path Management**: Fixed runtime directory provisioning - `demo.sh` now properly creates and syncs `~/herc` directory
- **Python Compatibility**: Replaced all `python` commands with `python3` for Ubuntu 20.04 compatibility
- **EBCDIC Support**: Added proper EBCDIC/binary data handling in TN3270 bridge to prevent UTF-8 decode errors
- **Pydantic Warning**: Renamed `validate` field to `validation_enabled` to avoid BaseModel shadowing
- **MVS File Check**: Enhanced MVS file detection to check both `herc_step8/mvs38j` and `~/herc/mvs38j`
- **Interactive Download**: Added prompt to automatically download MVS files if missing

### Added
- Runtime directory auto-provisioning with rsync to preserve MVS files
- Interactive MVS download prompt in demo.sh
- Fallback encoding support (UTF-8 → EBCDIC cp037 → latin-1)

### Changed
- All Python invocations now use `python3` explicitly
- `demo.sh` now uses rsync for intelligent file synchronization
- Bridge API field renamed from `validate` to `validation_enabled`

### Removed
- Obsolete fix documentation files:
  - CODE_REVIEW_FIXES.md
  - CRITICAL_DEFECTS_FOUND.md
  - CRITICAL_FIXES_ROUND2.md
  - FIX_IMPLEMENTATION_SUMMARY.md
  - herc_step8/CRITICAL_FIXES.md
  - herc_step8/FIXES_APPLIED.md

## [1.0.0] - 2025-09-27

### Initial Release
- IBM mainframe emulation with MVS 3.8J
- TN3270 bridge API with health monitoring
- AI agent for natural language control
- Claude Code integration
- YAML-based automation workflows
- Session recording and replay
- Automatic error recovery
- KICKS/CICS transaction support

## Architecture Notes

### Directory Structure
- **Repository**: `/mnt/c/python/mainframe_copilot/` - Source code only (~20MB)
- **Runtime**: `~/herc/` - Created automatically by demo.sh
- **MVS Files**: Downloaded separately to `~/herc/mvs38j/` (1.1GB)

### Key Components
1. **Hercules Emulator**: Runs MVS 3.8J operating system
2. **TN3270 Bridge**: REST API for mainframe interaction
3. **AI Agent**: Natural language command processor
4. **Flow System**: YAML-based automation sequences

### Compatibility
- Ubuntu 20.04+ (WSL2 or native)
- Python 3.8+
- Requires: tmux, s3270, netcat, jq

---
For detailed functionality review, see FUNCTIONALITY_REVIEW.md
For project structure, see PROJECT_FILEMAP.md