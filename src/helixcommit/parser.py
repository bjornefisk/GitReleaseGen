"""Conventional Commit parsing and classification utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

# Header pattern for conventional commits
# - Type: starts with letter, can contain letters, digits, hyphens
# - Scope: optional, in parentheses, can be empty or contain any chars except )
# - Breaking: optional ! before colon
# - Subject: can be empty (just whitespace after colon)
HEADER_PATTERN = re.compile(
    r"^(?P<type>[A-Za-z][A-Za-z0-9-]*)"
    r"(?:\((?P<scope>[^)]*)\))?"
    r"(?P<breaking>!)?:\s*(?P<subject>.*)$"
)

# Footer pattern - handles:
# - "Token: value" format
# - "Token #hash" format (e.g., "Fixes #123")
# - "Token:" with optional/empty value
FOOTER_PATTERN = re.compile(
    r"^(?P<token>[A-Za-z][A-Za-z0-9- ]*)(?::\s*(?P<value>.*)|\s+#(?P<hash>.+))$"
)

BREAKING_BODY_PATTERN = re.compile(
    r"^BREAKING(?:-| )CHANGE:\s*(?P<note>.+)$",
    re.IGNORECASE,
)

BREAKING_TOKENS = {"BREAKING CHANGE", "BREAKING-CHANGE"}

KNOWN_TYPES = {
    "build",
    "chore",
    "ci",
    "docs",
    "feat",
    "fix",
    "perf",
    "refactor",
    "style",
    "test",
    "revert",
}

TYPE_ALIASES = {
    "feature": "feat",
    "bugfix": "fix",
    "hotfix": "fix",
    "bug": "fix",
    "doc": "docs",
    "documentation": "docs",
    "perf": "perf",
    "performance": "perf",
    "tests": "test",
    "security": "fix",
    "deps": "chore",
}

FALLBACK_PATTERNS: Tuple[Tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\btest(s|ing)?\b", re.IGNORECASE), "test"),
    (re.compile(r"\bfix(ed|es|ing)?\b|\bbug\b", re.IGNORECASE), "fix"),
    (re.compile(r"\bfeat(ure)?\b", re.IGNORECASE), "feat"),
    (re.compile(r"\bdoc(s|ument(s|ation|ed|ing)?)?", re.IGNORECASE), "docs"),
    (re.compile(r"\brefactor\b", re.IGNORECASE), "refactor"),
    (re.compile(r"\bperf(ormance)?\b|\boptimi[sz]e\b", re.IGNORECASE), "perf"),
    (re.compile(r"\bbuild\b", re.IGNORECASE), "build"),
)


@dataclass
class ParsedCommitMessage:
    """Structured representation of a commit message."""

    type: Optional[str]
    scope: Optional[str]
    subject: str
    description: Optional[str]
    body: str
    footers: Dict[str, List[str]]
    breaking: bool
    breaking_descriptions: List[str]
    is_conventional: bool


def parse_commit_message(message: str) -> ParsedCommitMessage:
    """Parse a commit message into Conventional Commit components.

    Handles edge cases:
    - Empty or whitespace-only messages
    - Empty scope (e.g., "feat(): subject" -> scope is None)
    - Empty subject (e.g., "feat:" -> subject is "")
    - Unicode characters in body/footers
    """
    # Normalize line endings and strip leading/trailing newlines
    normalized = (message or "").replace("\r\n", "\n").strip()
    if not normalized:
        # Handle empty or whitespace-only messages
        return ParsedCommitMessage(
            type=None,
            scope=None,
            subject="",
            description=None,
            body="",
            footers={},
            breaking=False,
            breaking_descriptions=[],
            is_conventional=False,
        )

    lines = normalized.split("\n")
    header = lines[0] if lines else ""
    body_lines = lines[1:] if len(lines) > 1 else []

    match = HEADER_PATTERN.match(header.strip())
    raw_type = match.group("type") if match else None
    # Treat empty scope as None (e.g., "feat(): subject" -> scope is None)
    raw_scope = match.group("scope") if match else None
    scope = raw_scope.strip() if raw_scope and raw_scope.strip() else None
    # Handle empty subject gracefully
    raw_subject = match.group("subject") if match else header.strip()
    subject = raw_subject.strip() if raw_subject else ""
    type_name = normalize_type(raw_type)
    breaking = bool(match and match.group("breaking"))
    is_conventional = match is not None and type_name is not None

    body_lines = _strip_leading_blank_lines(body_lines)
    core_body_lines, footer_lines = _split_body_and_footers(body_lines)
    footers = _parse_footers(footer_lines)

    breaking_descriptions: List[str] = []
    for token, values in footers.items():
        token_key = token.upper().replace("-", " ")
        if token_key in BREAKING_TOKENS:
            breaking = True
            breaking_descriptions.extend(values)

    for line in core_body_lines:
        match_breaking = BREAKING_BODY_PATTERN.match(line.strip())
        if match_breaking:
            breaking = True
            breaking_descriptions.append(match_breaking.group("note"))

    body = "\n".join(core_body_lines).strip()
    description = _first_paragraph(core_body_lines)

    return ParsedCommitMessage(
        type=type_name,
        scope=scope,
        subject=subject,
        description=description,
        body=body,
        footers=footers,
        breaking=breaking,
        breaking_descriptions=breaking_descriptions,
        is_conventional=is_conventional,
    )


def normalize_type(raw_type: Optional[str]) -> Optional[str]:
    """Normalize a raw commit type into the known set."""

    if not raw_type:
        return None
    key = raw_type.lower()
    key = TYPE_ALIASES.get(key, key)
    if key not in KNOWN_TYPES:
        return None
    return key


def classify_change_type(message: str, *, default: str = "chore") -> str:
    """Guess a change type for arbitrary commit messages."""

    parsed = parse_commit_message(message)
    if parsed.type:
        return parsed.type
    lowered = message.lower()
    for pattern, change_type in FALLBACK_PATTERNS:
        if pattern.search(lowered):
            return change_type
    return default


def _strip_leading_blank_lines(lines: Iterable[str]) -> List[str]:
    iterator = iter(lines)
    stripped: List[str] = []
    skipping = True
    for line in iterator:
        if skipping and not line.strip():
            continue
        skipping = False
        stripped.append(line)
    return stripped


def _split_body_and_footers(lines: List[str]) -> Tuple[List[str], List[str]]:
    if not lines:
        return [], []
    # Identify the start of the footer block, if any.
    for idx, line in enumerate(lines):
        if FOOTER_PATTERN.match(line.strip()):
            if idx > 0 and lines[idx - 1].strip():
                continue
            candidate = lines[idx:]
            if all(_is_footer_line(item) for item in candidate):
                body = lines[:idx]
                footers = candidate
                break
    else:
        body = lines
        footers = []
    body = _trim_trailing_blank_lines(body)
    return body, footers


def _parse_footers(lines: List[str]) -> Dict[str, List[str]]:
    """Parse footer lines into a dictionary.

    Handles edge cases:
    - Empty footer values (e.g., "Token:")
    - Multi-line footer values (continuation lines starting with space/tab)
    - Hash-style references (e.g., "Fixes #123")
    """
    footers: Dict[str, List[str]] = {}
    current_token: Optional[str] = None
    for line in lines:
        if not line.strip():
            current_token = None
            continue
        match = FOOTER_PATTERN.match(line.strip())
        if match:
            token = match.group("token").strip()
            # Handle both "Token: value" and "Token #hash" formats
            hash_value = match.group("hash")
            raw_value = match.group("value")
            if hash_value is not None:
                value = f"#{hash_value.strip()}"
            elif raw_value is not None:
                value = raw_value.strip()
            else:
                value = ""
            current_token = token
            footers.setdefault(token, []).append(value)
            continue
        # Handle continuation lines for multi-line footer values
        if current_token and line.startswith((" ", "\t")):
            if footers[current_token]:
                footers[current_token][-1] += f"\n{line.strip()}"
        else:
            current_token = None
    return footers


def _is_footer_line(line: str) -> bool:
    if not line.strip():
        return True
    if FOOTER_PATTERN.match(line.strip()):
        return True
    return line.startswith((" ", "\t"))


def _trim_trailing_blank_lines(lines: List[str]) -> List[str]:
    trimmed = list(lines)
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()
    return trimmed


def _first_paragraph(lines: List[str]) -> Optional[str]:
    paragraph: List[str] = []
    for line in lines:
        if not line.strip():
            if paragraph:
                break
            continue
        paragraph.append(line.strip())
    if not paragraph:
        return None
    return " ".join(paragraph)


__all__ = [
    "ParsedCommitMessage",
    "classify_change_type",
    "normalize_type",
    "parse_commit_message",
]
