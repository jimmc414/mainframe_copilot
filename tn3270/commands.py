"""
Command Builder for TSO/ISPF Operations
Constructs properly formatted mainframe commands
"""

import logging
from typing import List, Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Types of mainframe commands"""
    TSO = "tso"
    ISPF = "ispf"
    JCL = "jcl"
    SDSF = "sdsf"
    SYSTEM = "system"


class CommandBuilder:
    """Build and format mainframe commands"""

    def __init__(self):
        """Initialize command builder"""
        self.max_command_length = 71  # TSO command line limit
        self.max_jcl_length = 71     # JCL line limit (columns 1-71)

    # TSO Commands
    def build_logon(self, userid: str, password: Optional[str] = None,
                    procedure: str = "LOGONPROC", acct: Optional[str] = None) -> str:
        """
        Build TSO LOGON command

        Args:
            userid: TSO user ID
            password: User password (if not prompting)
            procedure: Logon procedure name
            acct: Account number

        Returns:
            str: LOGON command
        """
        cmd = f"LOGON {userid}"

        if procedure:
            cmd += f" PROC({procedure})"

        if acct:
            cmd += f" ACCT({acct})"

        return cmd

    def build_listcat(self, dataset_pattern: Optional[str] = None,
                     level: Optional[str] = None) -> str:
        """
        Build LISTCAT command for dataset catalog listing

        Args:
            dataset_pattern: Dataset name pattern
            level: Dataset level qualifier

        Returns:
            str: LISTCAT command
        """
        cmd = "LISTCAT"

        if dataset_pattern:
            cmd += f" ENTRIES({dataset_pattern})"
        elif level:
            cmd += f" LEVEL({level})"

        return cmd

    def build_listds(self, dataset_pattern: str, members: bool = False) -> str:
        """
        Build LISTDS command for dataset information

        Args:
            dataset_pattern: Dataset name or pattern
            members: Include member list for PDS

        Returns:
            str: LISTDS command
        """
        cmd = f"LISTDS '{dataset_pattern}'"

        if members:
            cmd += " MEMBERS"

        return cmd

    def build_allocate(self, dataset_name: str, space_primary: int = 10,
                      space_secondary: int = 10, space_type: str = "TRACKS",
                      dsorg: str = "PS", recfm: str = "FB", lrecl: int = 80,
                      blksize: int = 0) -> str:
        """
        Build ALLOCATE command for new dataset

        Args:
            dataset_name: New dataset name
            space_primary: Primary space allocation
            space_secondary: Secondary space allocation
            space_type: TRACKS, CYLINDERS, or BLOCKS
            dsorg: Dataset organization (PS, PO, etc.)
            recfm: Record format (F, FB, V, VB, etc.)
            lrecl: Logical record length
            blksize: Block size (0 for system determined)

        Returns:
            str: ALLOCATE command
        """
        cmd = f"ALLOCATE DATASET('{dataset_name}')"
        cmd += f" NEW SPACE({space_type},{space_primary},{space_secondary})"
        cmd += f" DSORG({dsorg}) RECFM({recfm}) LRECL({lrecl})"

        if blksize > 0:
            cmd += f" BLKSIZE({blksize})"

        return cmd

    def build_delete(self, dataset_name: str, purge: bool = False) -> str:
        """
        Build DELETE command for dataset

        Args:
            dataset_name: Dataset to delete
            purge: Purge even if unexpired

        Returns:
            str: DELETE command
        """
        cmd = f"DELETE '{dataset_name}'"

        if purge:
            cmd += " PURGE"

        return cmd

    def build_submit(self, dataset_name: str, member: Optional[str] = None) -> str:
        """
        Build SUBMIT command for JCL execution

        Args:
            dataset_name: Dataset containing JCL
            member: Member name if PDS

        Returns:
            str: SUBMIT command
        """
        if member:
            return f"SUBMIT '{dataset_name}({member})'"
        else:
            return f"SUBMIT '{dataset_name}'"

    def build_status(self, jobname: Optional[str] = None) -> str:
        """
        Build STATUS command for job status

        Args:
            jobname: Specific job name to check

        Returns:
            str: STATUS command
        """
        if jobname:
            return f"STATUS {jobname}"
        else:
            return "STATUS"

    def build_cancel(self, jobname: str, purge: bool = False) -> str:
        """
        Build CANCEL command for job cancellation

        Args:
            jobname: Job to cancel
            purge: Purge output

        Returns:
            str: CANCEL command
        """
        cmd = f"CANCEL {jobname}"

        if purge:
            cmd += " PURGE"

        return cmd

    # ISPF Commands
    def build_ispf_start(self, panel: Optional[str] = None) -> str:
        """
        Build ISPF startup command

        Args:
            panel: Initial panel ID

        Returns:
            str: ISPF command
        """
        if panel:
            return f"ISPF PANEL({panel})"
        else:
            return "ISPF"

    def build_ispf_browse(self, dataset_name: str) -> str:
        """
        Build ISPF browse command

        Args:
            dataset_name: Dataset to browse

        Returns:
            str: Browse command
        """
        return f"BROWSE '{dataset_name}'"

    def build_ispf_edit(self, dataset_name: str, member: Optional[str] = None) -> str:
        """
        Build ISPF edit command

        Args:
            dataset_name: Dataset to edit
            member: Member name if PDS

        Returns:
            str: Edit command
        """
        if member:
            return f"EDIT '{dataset_name}({member})'"
        else:
            return f"EDIT '{dataset_name}'"

    # JCL Generation
    def build_jcl_header(self, jobname: str, account: str = "ACCT",
                        class: str = "A", msgclass: str = "X",
                        region: str = "0M") -> List[str]:
        """
        Build JCL job header

        Args:
            jobname: Job name (max 8 chars)
            account: Account information
            class: Job class
            msgclass: Message class
            region: Region size

        Returns:
            List[str]: JCL header lines
        """
        jobname = jobname[:8].upper()

        return [
            f"//{jobname} JOB ({account}),'MAINFRAME COPILOT',",
            f"//         CLASS={class},MSGCLASS={msgclass},",
            f"//         REGION={region},",
            "//         NOTIFY=&SYSUID,MSGLEVEL=(1,1)"
        ]

    def build_jcl_iefbr14(self, stepname: str = "STEP01") -> List[str]:
        """
        Build IEFBR14 utility step (null program)

        Args:
            stepname: Step name

        Returns:
            List[str]: JCL step lines
        """
        return [
            f"//{stepname} EXEC PGM=IEFBR14"
        ]

    def build_jcl_iebgener(self, stepname: str, input_dd: str,
                          output_dd: str) -> List[str]:
        """
        Build IEBGENER copy utility step

        Args:
            stepname: Step name
            input_dd: Input dataset
            output_dd: Output dataset

        Returns:
            List[str]: JCL step lines
        """
        return [
            f"//{stepname} EXEC PGM=IEBGENER",
            "//SYSPRINT DD SYSOUT=*",
            f"//SYSIN    DD DUMMY",
            f"//SYSUT1   DD DSN={input_dd},DISP=SHR",
            f"//SYSUT2   DD DSN={output_dd},",
            "//         DISP=(NEW,CATLG,DELETE),",
            "//         SPACE=(TRK,(5,5)),",
            "//         DCB=(RECFM=FB,LRECL=80,BLKSIZE=0)"
        ]

    def build_jcl_sort(self, stepname: str, input_dd: str,
                      output_dd: str, sort_fields: str) -> List[str]:
        """
        Build SORT utility step

        Args:
            stepname: Step name
            input_dd: Input dataset
            output_dd: Output dataset
            sort_fields: Sort control statements

        Returns:
            List[str]: JCL step lines
        """
        return [
            f"//{stepname} EXEC PGM=SORT",
            "//SYSOUT   DD SYSOUT=*",
            f"//SORTIN   DD DSN={input_dd},DISP=SHR",
            f"//SORTOUT  DD DSN={output_dd},",
            "//         DISP=(NEW,CATLG,DELETE),",
            "//         SPACE=(TRK,(5,5)),",
            "//         DCB=(RECFM=FB,LRECL=80,BLKSIZE=0)",
            "//SYSIN    DD *",
            sort_fields,
            "/*"
        ]

    def build_complete_jcl(self, jobname: str, steps: List[List[str]],
                          account: str = "ACCT") -> str:
        """
        Build complete JCL from header and steps

        Args:
            jobname: Job name
            steps: List of step line lists
            account: Account information

        Returns:
            str: Complete JCL
        """
        jcl_lines = self.build_jcl_header(jobname, account)

        for step_lines in steps:
            jcl_lines.append("//*")  # Step separator comment
            jcl_lines.extend(step_lines)

        return "\n".join(jcl_lines)

    # SDSF Commands
    def build_sdsf_command(self, command: str) -> str:
        """
        Build SDSF command

        Args:
            command: SDSF command (DA, O, H, etc.)

        Returns:
            str: Formatted SDSF command
        """
        return f"/{command}"

    # Utility Methods
    def format_dataset_name(self, dataset: str) -> str:
        """
        Format dataset name with proper quotes

        Args:
            dataset: Dataset name

        Returns:
            str: Properly formatted dataset name
        """
        # Remove existing quotes
        dataset = dataset.strip("'\"")

        # Add quotes if contains special characters or lowercase
        if any(c.islower() or c in "()@#$" for c in dataset):
            return f"'{dataset}'"

        return dataset

    def validate_dataset_name(self, dataset: str) -> bool:
        """
        Validate dataset name format

        Args:
            dataset: Dataset name to validate

        Returns:
            bool: True if valid
        """
        # Remove quotes for validation
        dataset = dataset.strip("'\"")

        # Check overall length (max 44 characters)
        if len(dataset) > 44:
            return False

        # Split into qualifiers
        qualifiers = dataset.split('.')

        # Must have at least one qualifier
        if len(qualifiers) == 0:
            return False

        # Check each qualifier
        for qualifier in qualifiers:
            # Max 8 characters per qualifier
            if len(qualifier) == 0 or len(qualifier) > 8:
                return False

            # First character must be alphabetic or national (@#$)
            if not (qualifier[0].isalpha() or qualifier[0] in '@#$'):
                return False

            # Other characters must be alphanumeric or national
            for char in qualifier[1:]:
                if not (char.isalnum() or char in '@#$'):
                    return False

        return True

    def truncate_command(self, command: str) -> str:
        """
        Truncate command to TSO line limit

        Args:
            command: Command to truncate

        Returns:
            str: Truncated command
        """
        if len(command) > self.max_command_length:
            logger.warning(f"Command truncated from {len(command)} to {self.max_command_length} characters")
            return command[:self.max_command_length]
        return command

    def split_long_command(self, command: str) -> List[str]:
        """
        Split long command into continuation lines

        Args:
            command: Long command

        Returns:
            List[str]: Command parts with continuation
        """
        if len(command) <= self.max_command_length:
            return [command]

        parts = []
        remaining = command

        while remaining:
            if len(remaining) <= self.max_command_length:
                parts.append(remaining)
                break
            else:
                # Find last space before limit
                split_pos = remaining[:self.max_command_length].rfind(' ')
                if split_pos == -1:
                    split_pos = self.max_command_length - 1

                # Add continuation character
                parts.append(remaining[:split_pos] + "-")
                remaining = remaining[split_pos:].lstrip()

        return parts