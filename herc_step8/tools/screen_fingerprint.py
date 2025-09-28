#!/usr/bin/env python3
"""Screen fingerprinting utilities for deterministic screen matching"""

import re
import hashlib
import json
import difflib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

def normalize_screen(ascii_text: str) -> str:
    """
    Normalize screen text for consistent fingerprinting
    - Trim trailing whitespace from each line
    - Normalize multiple spaces to single space
    - Strip leading/trailing blank lines
    """
    lines = ascii_text.split('\n')

    # Trim trailing whitespace from each line
    lines = [line.rstrip() for line in lines]

    # Remove leading blank lines
    while lines and not lines[0]:
        lines.pop(0)

    # Remove trailing blank lines
    while lines and not lines[-1]:
        lines.pop()

    return '\n'.join(lines)

def compute_digest(ascii_text: str) -> str:
    """Compute SHA256 digest of normalized screen text"""
    normalized = normalize_screen(ascii_text)
    return hashlib.sha256(normalized.encode()).hexdigest()

def match_screen(snapshot: Dict[str, Any], screen_id: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Match a screen snapshot against a screen ID definition

    Returns:
        (matched, rule_that_matched)
    """
    # Check dimensions if specified
    if 'match' in screen_id:
        match_rules = screen_id['match']

        # Check cols/rows if specified
        if 'cols' in match_rules and snapshot.get('cols') != match_rules['cols']:
            return False, None
        if 'rows' in match_rules and snapshot.get('rows') != match_rules['rows']:
            return False, None

    # Check stability requirements
    if 'stability' in screen_id:
        stability = screen_id['stability']
        if 'min_chars' in stability:
            ascii_len = len(snapshot.get('ascii', '').replace(' ', '').replace('\n', ''))
            if ascii_len < stability['min_chars']:
                return False, None

    # Check match rules
    ascii_text = snapshot.get('ascii', '')

    # Direct match rules at screen_id level
    if 'ascii_contains' in screen_id:
        if screen_id['ascii_contains'] in ascii_text:
            return True, f"ascii_contains: {screen_id['ascii_contains']}"

    if 'ascii_regex' in screen_id:
        if re.search(screen_id['ascii_regex'], ascii_text):
            return True, f"ascii_regex: {screen_id['ascii_regex']}"

    # Match rules in 'match' dict
    if 'match' in screen_id:
        match_rules = screen_id['match']

        # Check 'any' rules (OR logic)
        if 'any' in match_rules:
            for rule in match_rules['any']:
                if 'ascii_contains' in rule:
                    if rule['ascii_contains'] in ascii_text:
                        return True, f"ascii_contains: {rule['ascii_contains']}"

                if 'ascii_regex' in rule:
                    if re.search(rule['ascii_regex'], ascii_text):
                        return True, f"ascii_regex: {rule['ascii_regex']}"

        # Check 'all' rules (AND logic)
        if 'all' in match_rules:
            all_matched = True
            matched_rules = []

            for rule in match_rules['all']:
                matched = False

                if 'ascii_contains' in rule:
                    if rule['ascii_contains'] in ascii_text:
                        matched = True
                        matched_rules.append(f"ascii_contains: {rule['ascii_contains']}")

                if 'ascii_regex' in rule:
                    if re.search(rule['ascii_regex'], ascii_text):
                        matched = True
                        matched_rules.append(f"ascii_regex: {rule['ascii_regex']}")

                if not matched:
                    all_matched = False
                    break

            if all_matched and matched_rules:
                return True, " AND ".join(matched_rules)

    # Check 'any' rules at screen_id level
    if 'any' in screen_id:
        for rule in screen_id['any']:
            if 'ascii_contains' in rule:
                if rule['ascii_contains'] in ascii_text:
                    return True, f"ascii_contains: {rule['ascii_contains']}"

            if 'ascii_regex' in rule:
                if re.search(rule['ascii_regex'], ascii_text):
                    return True, f"ascii_regex: {rule['ascii_regex']}"

    return False, None

def save_golden(name: str, snapshot: Dict[str, Any], goldens_dir: Path = None) -> Path:
    """Save a golden snapshot"""
    if goldens_dir is None:
        goldens_dir = Path.home() / "herc" / "goldens"

    goldens_dir.mkdir(parents=True, exist_ok=True)

    # Save ASCII text
    text_file = goldens_dir / f"{name}.txt"
    with open(text_file, 'w') as f:
        f.write(snapshot.get('ascii', ''))

    # Save metadata (digest, dimensions, fields)
    meta_file = goldens_dir / f"{name}.json"
    metadata = {
        'name': name,
        'digest': snapshot.get('digest', compute_digest(snapshot.get('ascii', ''))),
        'rows': snapshot.get('rows', 24),
        'cols': snapshot.get('cols', 80),
        'field_count': len(snapshot.get('fields', [])),
        'cursor': snapshot.get('cursor', [0, 0])
    }

    with open(meta_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    return meta_file

def load_golden(name: str, goldens_dir: Path = None) -> Dict[str, Any]:
    """Load a golden snapshot"""
    if goldens_dir is None:
        goldens_dir = Path.home() / "herc" / "goldens"

    text_file = goldens_dir / f"{name}.txt"
    meta_file = goldens_dir / f"{name}.json"

    if not text_file.exists() or not meta_file.exists():
        raise FileNotFoundError(f"Golden snapshot '{name}' not found")

    with open(text_file, 'r') as f:
        ascii_text = f.read()

    with open(meta_file, 'r') as f:
        metadata = json.load(f)

    return {
        'ascii': ascii_text,
        'digest': metadata.get('digest'),
        'rows': metadata.get('rows', 24),
        'cols': metadata.get('cols', 80),
        'cursor': metadata.get('cursor', [0, 0]),
        'fields': []  # Fields not stored in golden
    }

def assert_golden(name: str, snapshot: Dict[str, Any], goldens_dir: Path = None) -> Tuple[bool, str]:
    """
    Assert current snapshot matches golden

    Returns:
        (matches, diff_output)
    """
    try:
        golden = load_golden(name, goldens_dir)
    except FileNotFoundError:
        return False, f"Golden '{name}' not found"

    current_digest = compute_digest(snapshot.get('ascii', ''))
    golden_digest = golden.get('digest')

    if current_digest == golden_digest:
        return True, "Digests match"

    # Generate diff
    golden_lines = golden.get('ascii', '').splitlines()
    current_lines = snapshot.get('ascii', '').splitlines()

    diff = difflib.unified_diff(
        golden_lines,
        current_lines,
        fromfile=f"golden/{name}",
        tofile="current",
        lineterm='',
        n=3
    )

    diff_output = '\n'.join(diff)
    return False, diff_output

def find_input_fields(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Find unprotected input fields in snapshot"""
    fields = snapshot.get('fields', [])
    return [f for f in fields if not f.get('protected', True)]

def get_field_at_label(snapshot: Dict[str, Any], label: str, offset: int = 1) -> Optional[Dict[str, Any]]:
    """
    Find field at offset from label text

    Returns field info with row/col position
    """
    ascii_text = snapshot.get('ascii', '')
    lines = ascii_text.split('\n')

    for row_idx, line in enumerate(lines):
        if label in line:
            label_pos = line.index(label)
            field_col = label_pos + len(label) + offset
            field_row = row_idx + 1  # 1-based

            # Wrap to next line if needed
            cols = snapshot.get('cols', 80)
            while field_col > cols:
                field_row += 1
                field_col -= cols

            return {
                'row': field_row,
                'col': field_col,
                'found': True
            }

    return None

# Predefined screen IDs
SCREEN_IDS = {
    'TSO_LOGON': {
        'name': 'TSO_LOGON',
        'match': {
            'any': [
                {'ascii_contains': 'TSO/E LOGON'},
                {'ascii_contains': 'ENTER USERID'},
                {'ascii_contains': 'Logon ===>'},
                {'ascii_regex': r'TK[345].*Logon'}
            ],
            'cols': 80,
            'rows': 24
        },
        'stability': {'min_chars': 200}
    },

    'TSO_PASSWORD': {
        'name': 'TSO_PASSWORD',
        'match': {
            'any': [
                {'ascii_contains': 'ENTER PASSWORD'},
                {'ascii_contains': 'ENTER CURRENT PASSWORD'},
                {'ascii_regex': r'PASSWORD.*FOR.*HERC'}
            ]
        }
    },

    'TSO_READY': {
        'name': 'TSO_READY',
        'match': {
            'all': [
                {'ascii_contains': 'READY'},
                {'ascii_regex': r'^\s*READY\s*$'}
            ]
        }
    },

    'KICKS_MENU': {
        'name': 'KICKS_MENU',
        'match': {
            'any': [
                {'ascii_contains': 'KICKS'},
                {'ascii_contains': 'KSGM'},
                {'ascii_contains': 'K I C K S'}
            ]
        }
    },

    'ERROR_SCREEN': {
        'name': 'ERROR_SCREEN',
        'match': {
            'any': [
                {'ascii_contains': 'ABEND'},
                {'ascii_contains': 'ERROR'},
                {'ascii_contains': 'REJECTED'},
                {'ascii_regex': r'IKJ\d{5}[EI]'}
            ]
        }
    }
}

if __name__ == "__main__":
    # Test code
    test_snapshot = {
        'ascii': 'Terminal CUU0C0\n\n  Logon ===> HERC02\n\n  READY\n',
        'rows': 24,
        'cols': 80,
        'fields': []
    }

    # Test normalization
    normalized = normalize_screen(test_snapshot['ascii'])
    print(f"Normalized: {repr(normalized)}")

    # Test digest
    digest = compute_digest(test_snapshot['ascii'])
    print(f"Digest: {digest[:16]}...")

    # Test matching
    matched, rule = match_screen(test_snapshot, SCREEN_IDS['TSO_LOGON'])
    print(f"Matches TSO_LOGON: {matched} ({rule})")

    matched, rule = match_screen(test_snapshot, SCREEN_IDS['TSO_READY'])
    print(f"Matches TSO_READY: {matched} ({rule})")