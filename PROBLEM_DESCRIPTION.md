# Mainframe Copilot - TSO Access Problem Description

## Executive Summary
We have a working MVS 3.8J mainframe emulator with a TN3270 API bridge that can successfully connect and manipulate the screen, but cannot access TSO/ISPF functionality because the available console is configured as a system operator console rather than a TSO terminal.

## Current Setup

### What's Installed and Working:

1. **Hercules Emulator** (v4.7.0.10978-SDL-g7d619f1e)
   - Running MVS 3.8J (TK5 Update 4)
   - Successfully booted and operational
   - Listening on port 3270 for TN3270 connections
   - Web interface on port 8038
   - Location: `~/herc/`
   - Running as: `hercules -f hercules.cnf`

2. **MVS 3.8J System Status**
   - JES2 is running (HASP messages visible in system log)
   - System is operational (can see periodic MF/1 report generation)
   - Console device: 0C0 (configured as system/operator console)

3. **TN3270 Bridge API** (Custom Python FastAPI application)
   - Successfully connects to mainframe on port 3270
   - REST API on port 8080 with endpoints:
     - `/screen` - Read current screen content
     - `/fill` - Type text at specific row/column
     - `/press` - Send keys (Enter, Clear, PF keys, etc.)
     - `/connect` / `/disconnect` - Manage connection
   - Uses `s3270` (scripted 3270 emulator) as backend
   - Location: `/mnt/c/python/mainframe_copilot/herc_step8/bridge/`

4. **Viewer Application**
   - Terminal-based UI showing real-time mainframe screen
   - Successfully displays the TK5 welcome screen
   - Updates when API sends commands

## What We're Trying to Do

Demonstrate automated mainframe control for CICS/JCL professionals by:
1. **Logging into TSO** with credentials (HERC02/CUL8TR)
2. **Navigating to ISPF** primary menu
3. **Submitting JCL jobs** and monitoring execution
4. **Executing CICS/KICKS transactions**
5. **Browsing and editing datasets**
6. **Showing SDSF job output**

## The Problem

### What's Happening:
- We can connect to the mainframe console at `127.0.0.1:3270`
- We see the TK5 welcome screen with "Logon ===>" prompt
- We can successfully type text on the screen (visible in viewer)
- We can press Enter and other keys

### What's NOT Working:
- Any attempt to login (TSO, LOGON, L HERC02, etc.) returns "INPUT NOT RECOGNIZED"
- The console at device address 0C0 appears to be a system/operator console, not a TSO terminal
- No TSO commands are accepted at this console
- Cannot access ISPF, submit jobs, or perform any user operations

### Root Cause:
The console we're connecting to (CUU 0C0) is configured as a master console or system operator console in the Hercules configuration, not as a TSO-enabled terminal. This console only shows the welcome screen and doesn't accept user logon commands.

## What We've Tried

1. **Different login commands:**
   - `TSO HERC02`
   - `LOGON HERC02`
   - `L HERC02`
   - `HERC02`
   - `TSO`
   - `LOGON`
   - All return "INPUT NOT RECOGNIZED"

2. **Different connection methods:**
   - Direct s3270 connection
   - Different terminal models (3278, 3279)
   - Web interface commands (but these go to Hercules, not MVS)

3. **Checked configuration:**
   - Only one 3270 port configured (3270)
   - No other console ports available
   - TSO appears to not be configured on accessible consoles

## What We Need Help With

1. **How to configure Hercules** to provide TSO-enabled terminals on additional ports (e.g., 3271-3279)

2. **How to modify the TK5 configuration** to enable TSO access on the existing console

3. **Alternative methods** to access TSO functionality with the current setup

4. **Verification that TSO is actually running** and how to start it if not

## Technical Details

### Hercules Configuration (key excerpts needed):
- Need to see: `~/herc/hercules.cnf` or `~/herc/mvs38j/mvs-tk5/conf/tk5.cnf`
- Looking for CONSOLE definitions and 3270 device configurations

### Current Console Definition:
- Device: 0C0
- Type: 3270 console
- Port: 3270
- Status: System/operator console (not TSO-enabled)

### System Environment:
- Running in WSL (Windows Subsystem for Linux)
- Ubuntu/Debian environment
- Python 3.10+
- All components running locally

## Desired Outcome

A working configuration where we can:
1. Connect to a TSO-enabled terminal
2. Successfully login with HERC02/CUL8TR
3. Access ISPF and all standard TSO functions
4. Demonstrate real mainframe operations for CICS/JCL professionals

## Contact for Help

Looking for assistance from:
- Hercules/MVS emulation experts
- TK5 configuration specialists
- Anyone who has successfully set up TSO access on Hercules

The goal is to demonstrate Claude Code (AI) controlling a real mainframe environment for automation purposes, but we're stuck at the console configuration level.