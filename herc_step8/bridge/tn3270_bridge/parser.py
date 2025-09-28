"""Field Parser - Parse ReadBuffer(Ascii) output to extract field attributes"""

import re
from typing import List, Dict, Any, Optional, Tuple

def parse_readbuffer_ascii(lines: List[str], rows: int = 24, cols: int = 80) -> List[Dict[str, Any]]:
    """
    Parse ReadBuffer(Ascii) output to extract field information

    Returns list of field dictionaries with:
    - row, col: Starting position (1-based)
    - len: Field length
    - protected: True if field is protected
    - attrs: Dictionary of attribute flags
    """
    fields = []
    current_field = None
    current_row = 1
    current_col = 1

    for line in lines:
        # Skip non-data lines
        if not line or line in ["ok", "error"]:
            continue
        if not line.startswith("data:"):
            continue

        # Remove "data:" prefix
        line = line[5:]

        # Parse the line for SF(...) markers
        col_offset = 0
        for match in re.finditer(r'SF\(([^)]+)\)', line):
            field_start = match.start()
            attrs_str = match.group(1)

            # If there's a current field, calculate its length
            if current_field:
                # Calculate field end position
                field_end_row = current_row
                field_end_col = col_offset + field_start

                # Calculate total length
                if field_end_row == current_field["row"]:
                    current_field["len"] = field_end_col - current_field["col"]
                else:
                    # Field spans multiple lines
                    current_field["len"] = (cols - current_field["col"] + 1) + \
                                         ((field_end_row - current_field["row"] - 1) * cols) + \
                                         field_end_col

                fields.append(current_field)

            # Parse attributes
            attrs = parse_field_attributes(attrs_str)

            # Create new field
            current_field = {
                "row": current_row,
                "col": current_col + col_offset + field_start,
                "len": 0,  # Will be calculated when we find the next field
                "protected": attrs.get("protected", False),
                "attrs": attrs
            }

            # Update column offset to account for SF marker
            col_offset += len(match.group(0))

        # Move to next line
        current_row += 1
        current_col = 1

    # Add the last field if exists
    if current_field:
        # Estimate length to end of screen
        remaining_on_line = cols - current_field["col"] + 1
        remaining_lines = rows - current_field["row"]
        current_field["len"] = remaining_on_line + (remaining_lines * cols)
        fields.append(current_field)

    return fields

def parse_field_attributes(attrs_str: str) -> Dict[str, Any]:
    """
    Parse field attribute string from SF(...)

    Common attribute bytes:
    - c0=20: Protected field
    - c0=10: Numeric field
    - c0=08: Intensified display
    - c0=0c: Non-display (hidden)
    - c0=04: Detectable
    - c0=30: Protected + Numeric
    - c0=28: Protected + Intensified
    """
    attrs = {
        "protected": False,
        "numeric": False,
        "intensified": False,
        "hidden": False,
        "modified": False,
        "detectable": False
    }

    # Parse key=value pairs
    for pair in attrs_str.split(','):
        pair = pair.strip()
        if '=' in pair:
            key, value = pair.split('=', 1)
            key = key.strip()
            value = value.strip()

            if key == "c0":
                # Parse character attribute byte
                try:
                    attr_byte = int(value, 16)
                    attrs["protected"] = bool(attr_byte & 0x20)
                    attrs["numeric"] = bool(attr_byte & 0x10)
                    attrs["intensified"] = bool(attr_byte & 0x08)
                    attrs["hidden"] = bool(attr_byte & 0x0C == 0x0C)
                    attrs["detectable"] = bool(attr_byte & 0x04)
                    attrs["modified"] = bool(attr_byte & 0x01)
                except ValueError:
                    pass

            elif key == "41":
                # Extended highlighting
                attrs["highlighting"] = value

            elif key == "42":
                # Foreground color
                attrs["fg_color"] = parse_color(value)

            elif key == "45":
                # Background color
                attrs["bg_color"] = parse_color(value)

    return attrs

def parse_color(color_code: str) -> str:
    """Parse 3270 color codes"""
    colors = {
        "f0": "neutral",
        "f1": "blue",
        "f2": "red",
        "f3": "pink",
        "f4": "green",
        "f5": "turquoise",
        "f6": "yellow",
        "f7": "white",
        "f8": "black",
        "f9": "deep_blue"
    }
    return colors.get(color_code.lower(), color_code)

def find_fields_at_position(fields: List[Dict[str, Any]], row: int, col: int) -> Optional[Dict[str, Any]]:
    """Find field at given position"""
    for field in fields:
        field_start = (field["row"] - 1) * 80 + field["col"]
        field_end = field_start + field["len"]
        pos = (row - 1) * 80 + col

        if field_start <= pos < field_end:
            return field

    return None

def find_unprotected_fields(fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return list of unprotected (input) fields"""
    return [f for f in fields if not f["attrs"]["protected"]]

def find_field_by_preceding_text(
    fields: List[Dict[str, Any]],
    ascii_text: str,
    label: str
) -> Optional[Dict[str, Any]]:
    """
    Find an unprotected field that follows a label in the screen text
    """
    # Split screen into lines
    lines = ascii_text.split('\n')

    # Search for label
    for row, line in enumerate(lines, 1):
        if label in line:
            # Found label, look for next unprotected field
            label_col = line.index(label) + len(label)

            # Check fields on same line first
            for field in find_unprotected_fields(fields):
                if field["row"] == row and field["col"] > label_col:
                    return field

            # Check fields on next lines
            for field in find_unprotected_fields(fields):
                if field["row"] > row:
                    return field

    return None