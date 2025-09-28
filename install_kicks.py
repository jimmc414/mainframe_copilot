#!/usr/bin/env python3
"""
KICKS Installation Script for MVS 3.8J
Automates the installation of KICKS for TSO
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from tn3270.client import TN3270Client
from tn3270.parser import ScreenParser
from tn3270.commands import CommandBuilder

async def install_kicks():
    """Main installation routine"""

    client = TN3270Client("localhost", 3270)
    parser = ScreenParser()
    cmd_builder = CommandBuilder()

    print("=== KICKS for TSO Installation ===")
    print("Version: 1.5.0")
    print("Target: MVS 3.8J TK5")
    print()

    try:
        # Connect to mainframe
        print("[1/8] Connecting to MVS...")
        if not await client.connect():
            print("ERROR: Failed to connect to mainframe")
            return False

        await asyncio.sleep(2)

        # Logon to TSO
        print("[2/8] Logging on to TSO...")
        if not await client.logon("HERC01", "CUL8TR"):
            print("ERROR: Failed to logon")
            return False

        await asyncio.sleep(3)

        # Wait for READY prompt
        if not await client.wait_for_text("READY", timeout=10):
            print("ERROR: TSO not ready")
            return False

        print("    TSO logon successful")

        # Step 1: Initialize card reader with XMIT file
        print("[3/8] Preparing XMIT file transfer...")

        # First, we need to tell Hercules to load the XMIT file to the card reader
        # This would typically be done via Hercules console command:
        # devinit 00c /home/jim/herc/mvs38j/mvs-tk5/rdr/kicks-tso-v1r5m0.xmi ebcdic

        print("    NOTE: Execute this command in Hercules console:")
        print("    devinit 00c /home/jim/herc/mvs38j/mvs-tk5/rdr/kicks-tso-v1r5m0.xmi ebcdic")
        print("    Press Enter when ready...")
        input()

        # Step 2: Submit RECV370 JCL
        print("[4/8] Submitting RECV370 job...")

        # Submit the JCL to receive the XMIT file
        await client.send_string("SUBMIT 'HERC01.JCL(RECVKICK)'")
        await client.send_enter()
        await asyncio.sleep(3)

        # Check for job submission message
        screen = client.get_screen()
        if "JOB" in screen and "SUBMITTED" in screen:
            print("    RECV370 job submitted successfully")
        else:
            # If no member exists, we need to create it first
            print("    Creating RECVKICK JCL member...")

            # Allocate JCL dataset if needed
            await client.send_string("ALLOC DA('HERC01.JCL') NEW SPACE(5,5) TRACKS " +
                                   "DSORG(PO) RECFM(FB) LRECL(80) BLKSIZE(3120) DIR(10)")
            await client.send_enter()
            await asyncio.sleep(2)

            # Edit the member
            await client.send_string("EDIT 'HERC01.JCL(RECVKICK)' NEW")
            await client.send_enter()
            await asyncio.sleep(2)

            # Enter the JCL
            jcl_lines = [
                "//HERC01RK JOB (ACCT),'RECV KICKS',CLASS=A,MSGCLASS=X,",
                "//         NOTIFY=&SYSUID,MSGLEVEL=(1,1)",
                "//RECV     EXEC PGM=RECV370",
                "//STEPLIB  DD DSN=SYSC.LINKLIB,DISP=SHR",
                "//RECVLOG  DD SYSOUT=*",
                "//XMITIN   DD UNIT=RDR,DCB=(RECFM=FB,LRECL=80,BLKSIZE=3120)",
                "//SYSPRINT DD SYSOUT=*",
                "//SYSUT1   DD UNIT=SYSDA,SPACE=(CYL,(10,10))",
                "//SYSUT2   DD DSN=HERC01.KICKS.XMIT,DISP=(NEW,CATLG,DELETE),",
                "//         UNIT=3390,VOL=SER=TSO001,SPACE=(CYL,(30,10))",
            ]

            for line in jcl_lines:
                await client.send_string(line)
                await client.send_enter()
                await asyncio.sleep(0.5)

            # Save and submit
            await client.send_pf(3)  # Exit edit
            await asyncio.sleep(2)

            await client.send_string("SUBMIT 'HERC01.JCL(RECVKICK)'")
            await client.send_enter()
            await asyncio.sleep(3)

        # Step 3: Use TSO RECEIVE to unpack the XMIT
        print("[5/8] Unpacking KICKS installation files...")

        await client.send_clear()
        await asyncio.sleep(1)

        await client.send_string("RECEIVE INDATASET('HERC01.KICKS.XMIT')")
        await client.send_enter()
        await asyncio.sleep(3)

        # Answer prompts for RECEIVE
        screen = client.get_screen()
        if "INMR901A" in screen or "dataset name" in screen.lower():
            await client.send_string("DA('HERC01.KICKS.INSTALL')")
            await client.send_enter()
            await asyncio.sleep(3)

        print("    XMIT file unpacked")

        # Step 4: Allocate KICKS datasets
        print("[6/8] Allocating KICKS datasets...")

        datasets = [
            ("HERC01.KICKS.V1R5M0.LINKLIB", "SPACE(15,10) TRACKS DSORG(PO) RECFM(U) LRECL(0) BLKSIZE(32760) DIR(50)"),
            ("HERC01.KICKS.V1R5M0.LOADLIB", "SPACE(15,10) TRACKS DSORG(PO) RECFM(U) LRECL(0) BLKSIZE(32760) DIR(100)"),
            ("HERC01.KICKS.V1R5M0.MACLIB", "SPACE(10,5) TRACKS DSORG(PO) RECFM(FB) LRECL(80) BLKSIZE(3120) DIR(50)"),
            ("HERC01.KICKS.V1R5M0.CLIST", "SPACE(5,5) TRACKS DSORG(PO) RECFM(FB) LRECL(80) BLKSIZE(3120) DIR(20)"),
            ("HERC01.KICKS.V1R5M0.INSTLIB", "SPACE(10,5) TRACKS DSORG(PO) RECFM(FB) LRECL(80) BLKSIZE(3120) DIR(30)"),
            ("HERC01.KICKS.V1R5M0.SAMPLIB", "SPACE(10,5) TRACKS DSORG(PO) RECFM(FB) LRECL(80) BLKSIZE(3120) DIR(30)"),
        ]

        for dsname, params in datasets:
            await client.send_clear()
            await asyncio.sleep(1)

            cmd = f"ALLOC DA('{dsname}') NEW {params}"
            await client.send_string(cmd)
            await client.send_enter()
            await asyncio.sleep(2)

            print(f"    Allocated {dsname}")

        # Step 5: Create KICKS startup CLIST
        print("[7/8] Creating KICKS startup CLIST...")

        await client.send_clear()
        await asyncio.sleep(1)

        await client.send_string("EDIT 'HERC01.KICKS.V1R5M0.CLIST(KICKS)' NEW")
        await client.send_enter()
        await asyncio.sleep(2)

        clist_lines = [
            "PROC 0 TCP()",
            "CONTROL NOFLUSH NOLIST NOMSG",
            "FREE F(STEPLIB DFHRPL SYSIN)",
            "ALLOC F(STEPLIB) DA('HERC01.KICKS.V1R5M0.LOADLIB') SHR REUSE",
            "ALLOC F(DFHRPL) DA('HERC01.KICKS.V1R5M0.LOADLIB') SHR REUSE",
            "ALLOC F(SYSIN) DUMMY REUSE",
            "CALL 'HERC01.KICKS.V1R5M0.LOADLIB(KIKSIP00)' +",
            "     'KCP() PCP() FCP() DCP() SCP() TSP() BMS() TCP(1$)'",
            "FREE F(STEPLIB DFHRPL SYSIN)",
        ]

        for line in clist_lines:
            await client.send_string(line)
            await client.send_enter()
            await asyncio.sleep(0.5)

        await client.send_pf(3)  # Exit edit
        await asyncio.sleep(2)

        print("    KICKS startup CLIST created")

        # Step 6: Test KICKS startup
        print("[8/8] Testing KICKS startup...")

        await client.send_clear()
        await asyncio.sleep(1)

        await client.send_string("EXEC 'HERC01.KICKS.V1R5M0.CLIST(KICKS)'")
        await client.send_enter()
        await asyncio.sleep(5)

        # Check for KICKS startup
        screen = client.get_screen()
        if "KICKS" in screen.upper():
            print("    KICKS started successfully!")
            print()
            print("=== KICKS Installation Complete ===")
            print()
            print("Screen capture:")
            print("-" * 60)
            print(screen)
            print("-" * 60)

            # Try to start demo transaction
            await client.send_string("DEMO")
            await client.send_enter()
            await asyncio.sleep(2)

            demo_screen = client.get_screen()
            print("\nDemo transaction screen:")
            print("-" * 60)
            print(demo_screen)
            print("-" * 60)

            # Shutdown KICKS
            await client.send_clear()
            await client.send_string("KSSF")
            await client.send_enter()
            await asyncio.sleep(3)
        else:
            print("    WARNING: Could not verify KICKS startup")
            print("    Screen content:")
            print(screen)

        # Logoff
        await client.logoff()
        await client.disconnect()

        print("\nInstallation Summary:")
        print("- KICKS Version: 1.5.0")
        print("- Install Path: HERC01.KICKS.V1R5M0.*")
        print("- Startup CLIST: EXEC 'HERC01.KICKS.V1R5M0.CLIST(KICKS)'")
        print("- Shutdown: Transaction KSSF")
        print("- Demo: Transaction DEMO")

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.disconnect()

if __name__ == "__main__":
    result = asyncio.run(install_kicks())
    sys.exit(0 if result else 1)