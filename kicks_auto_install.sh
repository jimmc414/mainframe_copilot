#!/bin/bash
# Automated KICKS installation script

# Function to send command to Hercules
send_hercules_cmd() {
    curl -s "http://localhost:8038/cgi-bin/tasks/cmd?cmd=$1" > /dev/null 2>&1
}

# Function to submit JCL via internal reader
submit_jcl() {
    local jcl_file=$1
    # Initialize internal reader with JCL file
    send_hercules_cmd "devinit+00c+$jcl_file"
    sleep 2
    # Interrupt to process the reader
    send_hercules_cmd "i+00c"
    sleep 5
}

echo "=== KICKS for TSO Installation Script ==="
echo ""

# Step 1: Card reader already initialized
echo "[1/6] Card reader initialized with KICKS XMIT file"

# Step 2: Submit RECV370 job via internal reader
echo "[2/6] Submitting RECV370 job..."
cd ~/herc/mvs38j/mvs-tk5
submit_jcl "jcl/recvkick.jcl"

# Wait for job completion
echo "    Waiting 30 seconds for RECV370 job to complete..."
sleep 30

# Step 3: Manual steps required
echo ""
echo "[3/6] Manual steps required:"
echo ""
echo "Please use c3270 to connect and execute these commands:"
echo ""
echo "1. Connect to TSO:"
echo "   c3270 localhost:3270"
echo ""
echo "2. Logon:"
echo "   LOGON HERC02"
echo "   Password: CUL8TR"
echo ""
echo "3. Wait for READY prompt, then unpack XMIT:"
echo "   RECEIVE INDATASET('HERC02.KICKS.XMIT')"
echo "   When prompted for dataset name:"
echo "   DA('HERC02.KICKS.INSTALL')"
echo ""
echo "4. Allocate KICKS datasets (copy/paste each line):"
cat << 'EOF'
ALLOC DA('HERC02.KICKS.V1R5M0.LINKLIB') NEW SPACE(15,10) TRACKS -
      DSORG(PO) RECFM(U) LRECL(0) BLKSIZE(32760) DIR(50)

ALLOC DA('HERC02.KICKS.V1R5M0.LOADLIB') NEW SPACE(15,10) TRACKS -
      DSORG(PO) RECFM(U) LRECL(0) BLKSIZE(32760) DIR(100)

ALLOC DA('HERC02.KICKS.V1R5M0.MACLIB') NEW SPACE(10,5) TRACKS -
      DSORG(PO) RECFM(FB) LRECL(80) BLKSIZE(3120) DIR(50)

ALLOC DA('HERC02.KICKS.V1R5M0.CLIST') NEW SPACE(5,5) TRACKS -
      DSORG(PO) RECFM(FB) LRECL(80) BLKSIZE(3120) DIR(20)
EOF

echo ""
echo "5. Create KICKS startup CLIST:"
echo "   EDIT 'HERC02.KICKS.V1R5M0.CLIST(KICKS)' NEW"
echo ""
echo "   Enter these lines:"
cat << 'EOF'
PROC 0 TCP()
CONTROL NOFLUSH NOLIST NOMSG
FREE F(STEPLIB DFHRPL SYSIN)
ALLOC F(STEPLIB) DA('HERC02.KICKS.V1R5M0.LOADLIB') SHR REUSE
ALLOC F(DFHRPL) DA('HERC02.KICKS.V1R5M0.LOADLIB') SHR REUSE
ALLOC F(SYSIN) DUMMY REUSE
CALL 'HERC02.KICKS.V1R5M0.LOADLIB(KIKSIP00)' +
     'KCP() PCP() FCP() DCP() SCP() TSP() BMS() TCP(1$)'
FREE F(STEPLIB DFHRPL SYSIN)
EOF

echo ""
echo "   Save with PF3"
echo ""
echo "6. Test KICKS:"
echo "   EXEC 'HERC02.KICKS.V1R5M0.CLIST(KICKS)'"
echo ""
echo "7. Shutdown KICKS:"
echo "   KSSF"
echo ""
echo "8. Logoff from TSO:"
echo "   LOGOFF"
echo ""