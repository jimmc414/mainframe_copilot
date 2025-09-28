# MVS 3.8J Setup Guide

## Why MVS Files Are Separate

The MVS 3.8J system files are not included in this repository because:

1. **Size**: The complete MVS TK5 distribution is approximately 1.1GB
   - DASD disk images: 260MB
   - Hercules binaries: 161MB
   - Documentation: 101MB
   - Other files: ~500MB

2. **Binary Files**: Most MVS files are binary disk images that don't belong in Git

3. **Platform-Specific**: Hercules emulator binaries vary by operating system

4. **Licensing**: MVS should be obtained from official distribution sources

## Quick Setup

### Automatic Download (Recommended)

Run the provided download script:

```bash
/mnt/c/python/mainframe_copilot/scripts/download_mvs.sh
```

This script will:
- Check available disk space (needs ~3GB during installation)
- Download MVS TK5 from official sources
- Extract to `~/herc/mvs38j/mvs-tk5`
- Set up proper permissions
- Verify the installation

### Manual Download

If the automatic download fails:

1. **Download MVS TK5**:
   - Primary source: http://wotho.ethz.ch/tk4-/tk4-_v1.00_current.zip
   - Backup source: https://github.com/MVS38J/tk4/releases/

2. **Create directory structure**:
   ```bash
   mkdir -p ~/herc/mvs38j
   cd ~/herc/mvs38j
   ```

3. **Extract the archive**:
   ```bash
   unzip tk4-_v1.00_current.zip
   # Rename if needed
   mv tk4-* mvs-tk5
   ```

4. **Set permissions**:
   ```bash
   chmod +x mvs-tk5/mvs mvs-tk5/start_herc
   chmod 644 mvs-tk5/dasd/*
   ```

## Verification

After installation, verify MVS is properly installed:

```bash
# Check required files exist
ls -la ~/herc/mvs38j/mvs-tk5/conf/tk5.cnf
ls -la ~/herc/mvs38j/mvs-tk5/dasd/mvsres.3350

# Check total size (should be ~1.1GB)
du -sh ~/herc/mvs38j/mvs-tk5
```

## Directory Structure

After successful installation:

```
~/herc/
├── mvs38j/
│   ├── mvs-tk5/
│   │   ├── conf/           # Hercules configuration
│   │   │   └── tk5.cnf     # Main config file
│   │   ├── dasd/           # DASD disk images (260MB)
│   │   │   ├── mvsres.3350 # System residence volume
│   │   │   ├── mvs000.3350 # User volume
│   │   │   └── ...         # Other volumes
│   │   ├── hercules/       # Emulator binaries (161MB)
│   │   ├── doc/            # Documentation (101MB)
│   │   ├── jcl/            # Sample JCL
│   │   ├── tape/           # Tape images
│   │   └── scripts/        # Utility scripts
│   └── mvs-tk5.zip        # Original archive (can be deleted)
├── ai/                     # AI agent (linked from repo)
├── bridge/                 # TN3270 bridge (linked from repo)
├── flows/                  # Workflows (linked from repo)
└── logs/                   # Runtime logs
```

## First Start

After MVS installation:

1. **Test Hercules**:
   ```bash
   cd ~/herc/mvs38j/mvs-tk5
   hercules -f conf/tk5.cnf
   # Press Ctrl+C to exit
   ```

2. **Start the full system**:
   ```bash
   cd ~/herc
   ./demo.sh
   ```

## Troubleshooting

### Download Fails

If the automatic download fails:
- Check internet connection
- Try the backup URL
- Download manually using a browser
- Check available disk space (need 3GB free)

### Extraction Fails

Common issues:
- Corrupted download: Re-download the file
- Insufficient space: Need 3GB during extraction
- Wrong format: Ensure it's a ZIP file, not TAR

### Hercules Won't Start

Check:
- File permissions: `chmod +x` on scripts
- Configuration exists: `conf/tk5.cnf` present
- DASD files intact: Check file sizes match

### MVS Won't Boot

Symptoms:
- Hercules starts but no TN3270 connection
- IPL fails or hangs

Solutions:
- Check DASD files aren't corrupted
- Verify all required volumes present
- Try manual IPL: `ipl 00c` in Hercules console

## Alternative MVS Distributions

While TK5 is recommended, alternatives include:

1. **TK4-**: Earlier version, smaller size
2. **MVS/CE**: Community Edition with more software
3. **Custom builds**: From MVS Turnkey archive

All should work with minor configuration adjustments.

## Space Requirements

### During Installation
- Download: 500MB
- Extraction: 1.1GB
- Temporary: 500MB
- **Total needed**: ~3GB

### After Installation
- MVS TK5: 1.1GB
- Logs: 100MB (grows over time)
- **Total needed**: ~1.5GB

## Security Notes

The MVS TK5 distribution includes:
- Demo user accounts (HERC01, HERC02, etc.)
- Default passwords (CUL8TR, PASS4U, etc.)
- Sample data and programs

**Never use these credentials or configurations in production!**

## Getting Help

1. Check the main README: `/mnt/c/python/mainframe_copilot/README.md`
2. Review the runbook: `~/herc/docs/RUNBOOK.md`
3. Hercules documentation: http://www.hercules-390.org/
4. TK5 documentation: In `~/herc/mvs38j/mvs-tk5/doc/`

## Next Steps

After successful MVS installation:

1. Start the system: `cd ~/herc && ./demo.sh`
2. Test connection: `curl http://127.0.0.1:8080/healthz`
3. Try TSO login: Use credentials HERC02/CUL8TR
4. Run sample workflows in `~/herc/flows/`
5. Integrate with Claude Code

---

**Note**: This is a demonstration system. For production mainframe access, connect directly to your enterprise mainframe using the TN3270 bridge with appropriate security configurations.