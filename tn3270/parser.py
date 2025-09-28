"""
3270 Screen Parser
Parses and interprets 3270 screen content, fields, and attributes
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ScreenType(Enum):
    """Common mainframe screen types"""
    UNKNOWN = "unknown"
    VTAM_LOGO = "vtam_logo"
    TSO_LOGON = "tso_logon"
    TSO_READY = "tso_ready"
    ISPF_PRIMARY = "ispf_primary"
    ISPF_EDIT = "ispf_edit"
    ISPF_BROWSE = "ispf_browse"
    ISPF_DATASET_LIST = "ispf_dataset_list"
    SDSF_PRIMARY = "sdsf_primary"
    SDSF_STATUS = "sdsf_status"
    JCL_SUBMIT = "jcl_submit"
    ERROR = "error"
    MESSAGE = "message"


@dataclass
class Field:
    """Represents a field on the 3270 screen"""
    row: int
    col: int
    length: int
    protected: bool
    numeric: bool
    highlighted: bool
    content: str = ""


@dataclass
class ScreenInfo:
    """Parsed screen information"""
    type: ScreenType
    title: str
    fields: List[Field]
    messages: List[str]
    cursor_position: Tuple[int, int]
    raw_content: str


class ScreenParser:
    """Parser for 3270 screen content"""

    def __init__(self):
        """Initialize screen parser"""
        self.screen_patterns = {
            ScreenType.VTAM_LOGO: [
                r"Enter LOGON",
                r"VTAM",
                r"TK5.*Update"
            ],
            ScreenType.TSO_LOGON: [
                r"TSO/E LOGON",
                r"Enter LOGON parameters",
                r"ENTER PASSWORD"
            ],
            ScreenType.TSO_READY: [
                r"READY",
                r"^\*{3}$"
            ],
            ScreenType.ISPF_PRIMARY: [
                r"ISPF Primary Option Menu",
                r"Option ===>",
                r"0\s+Settings",
                r"1\s+Browse"
            ],
            ScreenType.ISPF_EDIT: [
                r"EDIT.*Entry Panel",
                r"ISPF Editor",
                r"Command ===>"
            ],
            ScreenType.ISPF_BROWSE: [
                r"BROWSE.*Entry Panel",
                r"Command ===>"
            ],
            ScreenType.ISPF_DATASET_LIST: [
                r"DSLIST",
                r"Data Set List",
                r"Command ===>"
            ],
            ScreenType.SDSF_PRIMARY: [
                r"SDSF.*MENU",
                r"SDSF Primary Option Menu"
            ],
            ScreenType.SDSF_STATUS: [
                r"SDSF.*STATUS",
                r"COMMAND INPUT ===>"
            ],
            ScreenType.JCL_SUBMIT: [
                r"JOB.*SUBMITTED",
                r"IKJ56250I"
            ],
            ScreenType.ERROR: [
                r"ABEND",
                r"ERROR",
                r"INVALID",
                r"\*{3}\s+E"
            ],
            ScreenType.MESSAGE: [
                r"MESSAGE",
                r"IEE",
                r"IKJ"
            ]
        }

    def parse_screen(self, screen_content: str, cursor_pos: Tuple[int, int] = (1, 1)) -> ScreenInfo:
        """
        Parse 3270 screen content

        Args:
            screen_content: Raw screen content string
            cursor_pos: Current cursor position

        Returns:
            ScreenInfo: Parsed screen information
        """
        screen_type = self.identify_screen_type(screen_content)
        title = self.extract_title(screen_content)
        fields = self.extract_fields(screen_content)
        messages = self.extract_messages(screen_content)

        return ScreenInfo(
            type=screen_type,
            title=title,
            fields=fields,
            messages=messages,
            cursor_position=cursor_pos,
            raw_content=screen_content
        )

    def identify_screen_type(self, screen_content: str) -> ScreenType:
        """
        Identify the type of screen based on content patterns

        Args:
            screen_content: Raw screen content

        Returns:
            ScreenType: Identified screen type
        """
        for screen_type, patterns in self.screen_patterns.items():
            matches = 0
            for pattern in patterns:
                if re.search(pattern, screen_content, re.IGNORECASE | re.MULTILINE):
                    matches += 1

            # If at least half of patterns match, consider it identified
            if matches >= len(patterns) / 2:
                logger.debug(f"Identified screen type: {screen_type}")
                return screen_type

        return ScreenType.UNKNOWN

    def extract_title(self, screen_content: str) -> str:
        """
        Extract screen title from content

        Args:
            screen_content: Raw screen content

        Returns:
            str: Screen title or empty string
        """
        lines = screen_content.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if len(line) > 10 and not line.startswith('*'):
                # Look for typical title patterns
                if any(keyword in line.upper() for keyword in
                       ['ISPF', 'TSO', 'SDSF', 'MENU', 'PANEL', 'VTAM']):
                    return line
                # Check if line is mostly uppercase (common for titles)
                if sum(1 for c in line if c.isupper()) > len(line) * 0.6:
                    return line

        return ""

    def extract_fields(self, screen_content: str) -> List[Field]:
        """
        Extract input fields from screen

        Args:
            screen_content: Raw screen content

        Returns:
            List[Field]: List of identified fields
        """
        fields = []
        lines = screen_content.split('\n') if '\n' in screen_content else self._split_screen_lines(screen_content)

        # Common field patterns
        field_patterns = [
            (r'(.*?)===>\s*(.*)$', 'input'),  # ISPF command fields
            (r'(.*?):\s+_+', 'input'),        # Underscored input fields
            (r'(.*?):\s*\[.*?\]', 'input'),   # Bracketed fields
            (r'(.*?)\.{3,}\s*(.*)$', 'input'),  # Dotted fields
        ]

        for row, line in enumerate(lines, 1):
            for pattern, field_type in field_patterns:
                match = re.search(pattern, line)
                if match:
                    col = match.start(2) if len(match.groups()) > 1 else match.start()
                    length = len(match.group(2)) if len(match.groups()) > 1 else 20

                    field = Field(
                        row=row,
                        col=col + 1,  # Convert to 1-based
                        length=max(length, 20),  # Minimum field length
                        protected=False,
                        numeric=False,
                        highlighted=False,
                        content=match.group(2) if len(match.groups()) > 1 else ""
                    )
                    fields.append(field)
                    break

        return fields

    def extract_messages(self, screen_content: str) -> List[str]:
        """
        Extract system messages from screen

        Args:
            screen_content: Raw screen content

        Returns:
            List[str]: List of messages
        """
        messages = []
        lines = screen_content.split('\n') if '\n' in screen_content else self._split_screen_lines(screen_content)

        # Common message patterns
        message_patterns = [
            r'^\*{3}\s+(.+)$',  # TSO messages (*** MESSAGE)
            r'^IKJ\w+\s+(.+)$',  # TSO messages
            r'^IEE\w+\s+(.+)$',  # System messages
            r'^IEF\w+\s+(.+)$',  # Job messages
            r'^\$HASP\w+\s+(.+)$',  # JES2 messages
            r'^IST\w+\s+(.+)$',  # VTAM messages
        ]

        for line in lines:
            line = line.strip()
            if not line:
                continue

            for pattern in message_patterns:
                match = re.match(pattern, line)
                if match:
                    messages.append(line)
                    break

        return messages

    def _split_screen_lines(self, screen_content: str, width: int = 80) -> List[str]:
        """
        Split screen content into lines based on fixed width

        Args:
            screen_content: Raw screen content
            width: Screen width (default 80)

        Returns:
            List[str]: List of screen lines
        """
        lines = []
        for i in range(0, len(screen_content), width):
            lines.append(screen_content[i:i+width])
        return lines

    def find_input_field(self, screen_info: ScreenInfo, label: str) -> Optional[Field]:
        """
        Find input field by label

        Args:
            screen_info: Parsed screen information
            label: Field label to search for

        Returns:
            Optional[Field]: Found field or None
        """
        label_upper = label.upper()
        lines = screen_info.raw_content.split('\n') if '\n' in screen_info.raw_content else \
                self._split_screen_lines(screen_info.raw_content)

        for row, line in enumerate(lines, 1):
            if label_upper in line.upper():
                # Look for fields on the same line
                for field in screen_info.fields:
                    if field.row == row:
                        return field

        return None

    def get_command_field(self, screen_info: ScreenInfo) -> Optional[Field]:
        """
        Get the command input field (usually marked with ===>)

        Args:
            screen_info: Parsed screen information

        Returns:
            Optional[Field]: Command field or None
        """
        # Look for common command field patterns
        for field in screen_info.fields:
            line_content = self._get_line_content(screen_info.raw_content, field.row)
            if '===>' in line_content or 'COMMAND' in line_content.upper():
                return field

        # Return first unprotected field as fallback
        for field in screen_info.fields:
            if not field.protected:
                return field

        return None

    def _get_line_content(self, screen_content: str, row: int) -> str:
        """
        Get content of specific screen line

        Args:
            screen_content: Raw screen content
            row: Row number (1-based)

        Returns:
            str: Line content
        """
        lines = screen_content.split('\n') if '\n' in screen_content else \
                self._split_screen_lines(screen_content)

        if 1 <= row <= len(lines):
            return lines[row - 1]
        return ""

    def is_error_screen(self, screen_info: ScreenInfo) -> bool:
        """
        Check if screen contains error messages

        Args:
            screen_info: Parsed screen information

        Returns:
            bool: True if error screen
        """
        if screen_info.type == ScreenType.ERROR:
            return True

        error_keywords = ['ERROR', 'INVALID', 'ABEND', 'FAILED', 'NOT AUTHORIZED']
        content_upper = screen_info.raw_content.upper()

        return any(keyword in content_upper for keyword in error_keywords)

    def extract_dataset_list(self, screen_content: str) -> List[Dict[str, str]]:
        """
        Extract dataset information from ISPF dataset list screen

        Args:
            screen_content: Raw screen content

        Returns:
            List[Dict[str, str]]: List of datasets with properties
        """
        datasets = []
        lines = screen_content.split('\n') if '\n' in screen_content else \
                self._split_screen_lines(screen_content)

        # Look for dataset list pattern (usually starts after header)
        in_dataset_list = False
        dataset_pattern = re.compile(r'^([A-Z0-9$#@]+(?:\.[A-Z0-9$#@]+)*)\s+')

        for line in lines:
            if 'VOLUME' in line.upper() and 'DSORG' in line.upper():
                in_dataset_list = True
                continue

            if in_dataset_list:
                match = dataset_pattern.match(line)
                if match:
                    dataset_name = match.group(1)
                    # Extract additional info if available
                    parts = line.split()
                    dataset_info = {
                        'name': dataset_name,
                        'volume': parts[1] if len(parts) > 1 else '',
                        'dsorg': parts[2] if len(parts) > 2 else '',
                        'recfm': parts[3] if len(parts) > 3 else ''
                    }
                    datasets.append(dataset_info)

        return datasets

    def extract_job_info(self, screen_content: str) -> Optional[Dict[str, str]]:
        """
        Extract job submission information

        Args:
            screen_content: Raw screen content

        Returns:
            Optional[Dict[str, str]]: Job information or None
        """
        # Look for job submission patterns
        job_pattern = re.compile(r'JOB\s+([A-Z0-9]+)\s+.*SUBMITTED')
        job_number_pattern = re.compile(r'JOB(\d+)')

        match = job_pattern.search(screen_content)
        if match:
            job_name = match.group(1)

            # Try to find job number
            job_number = None
            number_match = job_number_pattern.search(screen_content)
            if number_match:
                job_number = number_match.group(1)

            return {
                'job_name': job_name,
                'job_number': job_number or 'UNKNOWN',
                'status': 'SUBMITTED'
            }

        return None