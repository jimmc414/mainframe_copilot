# KICKS for TSO Installation Status

## Completed Steps

### 1. KICKS Package Downloaded
- Source: GitHub (moshix/kicks)
- Version: 1.5.0
- File: kicks-tso-v1r5m0.xmi (XMIT format)
- Location: ~/herc/mvs38j/mvs-tk5/rdr/

### 2. Card Reader Initialized
- Command executed: `devinit 00c rdr/kicks-tso-v1r5m0.xmi ebcdic`
- Status: Successfully initialized
- Ready for RECV370 processing

### 3. JCL Created
- File: /home/jim/herc/mvs38j/mvs-tk5/jcl/recvkick.jcl
- Purpose: Process XMIT file via RECV370
- Target dataset: HERC02.KICKS.XMIT

### 4. Installation Scripts Created
- kicks_install.sh - Manual installation guide
- kicks_auto_install.sh - Semi-automated script
- install_kicks.py - Python automation (requires manual TSO steps)

## Manual Steps Required to Complete Installation

Connect to TSO using c3270:
```bash
c3270 localhost:3270
```

### Step 1: Logon to TSO
```
LOGON HERC02
Password: CUL8TR
```

### Step 2: Submit RECV370 Job
After READY prompt:
```
SUBMIT *
```

Then paste this JCL:
```jcl
//HERC02RK JOB (ACCT),'RECV KICKS',CLASS=A,MSGCLASS=X,
//         NOTIFY=&SYSUID,MSGLEVEL=(1,1)
//RECV     EXEC PGM=RECV370
//STEPLIB  DD DSN=SYSC.LINKLIB,DISP=SHR
//RECVLOG  DD SYSOUT=*
//XMITIN   DD UNIT=RDR,DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)
//SYSPRINT DD SYSOUT=*
//SYSUT1   DD DSN=&&TEMP1,DISP=(NEW,DELETE),
//         UNIT=SYSDA,SPACE=(CYL,(10,10))
//SYSUT2   DD DSN=HERC02.KICKS.XMIT,DISP=(NEW,CATLG,DELETE),
//         UNIT=3390,VOL=SER=TSO001,SPACE=(CYL,(30,10))
/*
//
```

Press Enter, then type `/*` and press Enter again to submit.

### Step 3: Wait for Job Completion
Check job status:
```
STATUS
```

### Step 4: Unpack XMIT File
```
RECEIVE INDATASET('HERC02.KICKS.XMIT')
```
When prompted for dataset name:
```
DA('HERC02.KICKS.INSTALL')
```

### Step 5: Allocate KICKS Datasets
Execute each ALLOC command:
```
ALLOC DA('HERC02.KICKS.V1R5M0.LINKLIB') NEW SPACE(15,10) TRACKS DSORG(PO) RECFM(U) LRECL(0) BLKSIZE(32760) DIR(50)

ALLOC DA('HERC02.KICKS.V1R5M0.LOADLIB') NEW SPACE(15,10) TRACKS DSORG(PO) RECFM(U) LRECL(0) BLKSIZE(32760) DIR(100)

ALLOC DA('HERC02.KICKS.V1R5M0.MACLIB') NEW SPACE(10,5) TRACKS DSORG(PO) RECFM(FB) LRECL(80) BLKSIZE(3120) DIR(50)

ALLOC DA('HERC02.KICKS.V1R5M0.CLIST') NEW SPACE(5,5) TRACKS DSORG(PO) RECFM(FB) LRECL(80) BLKSIZE(3120) DIR(20)
```

### Step 6: Create KICKS Startup CLIST
```
EDIT 'HERC02.KICKS.V1R5M0.CLIST(KICKS)' NEW
```

Enter these lines in the editor:
```
PROC 0 TCP()
CONTROL NOFLUSH NOLIST NOMSG
FREE F(STEPLIB DFHRPL SYSIN)
ALLOC F(STEPLIB) DA('HERC02.KICKS.V1R5M0.LOADLIB') SHR REUSE
ALLOC F(DFHRPL) DA('HERC02.KICKS.V1R5M0.LOADLIB') SHR REUSE
ALLOC F(SYSIN) DUMMY REUSE
CALL 'HERC02.KICKS.V1R5M0.LOADLIB(KIKSIP00)' +
     'KCP() PCP() FCP() DCP() SCP() TSP() BMS() TCP(1$)'
FREE F(STEPLIB DFHRPL SYSIN)
```

Save with PF3.

### Step 7: Test KICKS
```
EXEC 'HERC02.KICKS.V1R5M0.CLIST(KICKS)'
```

If successful, you should see the KICKS startup screen.

### Step 8: Test Demo Transaction
```
DEMO
```

### Step 9: Shutdown KICKS
```
KSSF
```

### Step 10: Logoff
```
LOGOFF
```

## Current Status
- **Card reader initialized with XMIT file**: ✓
- **JCL prepared**: ✓
- **Manual TSO steps**: PENDING
- **KICKS datasets allocated**: PENDING
- **KICKS startup CLIST created**: PENDING
- **KICKS tested**: PENDING

## Next Actions
1. Connect to TSO via c3270
2. Follow manual steps above
3. Verify KICKS installation
4. Document test results

## Files Created
- `/home/jim/herc/mvs38j/mvs-tk5/rdr/kicks-tso-v1r5m0.xmi` - KICKS XMIT file
- `/home/jim/herc/mvs38j/mvs-tk5/jcl/recvkick.jcl` - RECV370 JCL
- `/mnt/c/python/mainframe_copilot/kicks_install.sh` - Manual guide
- `/mnt/c/python/mainframe_copilot/kicks_auto_install.sh` - Semi-automated script
- `/mnt/c/python/mainframe_copilot/install_kicks.py` - Python automation attempt

## Notes
- Using HERC02 user to avoid conflict with HERC01
- KICKS version 1.5.0 is the latest available
- Installation requires manual TSO interaction due to 3270 protocol limitations
- Card reader (device 00C) successfully initialized with XMIT file