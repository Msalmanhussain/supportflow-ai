"""Load fictional demo policy Markdown from a fixed application directory.

Customer input never selects filesystem paths. Only files under
``app/policy_docs/`` that match ``*.md`` are read.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# Fixed app-owned directory — never derived from request input.
POLICY_DOCS_DIR = Path(__file__).resolve().parents[1] / "policy_docs"

_FRONT_MATTER_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n(.*)$",
    re.DOTALL,
)
_SECTION_RE = re.compile(
    r"^##\s+section:\s*([A-Za-z0-9][A-Za-z0-9_-]*)\s*$",
    re.MULTILINE,
)
_META_LINE_RE = re.compile(
    r"^(document_id|title|version|demo_label):\s*(.+?)\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class PolicySection:
    document_id: str
    title: str
    version: str
    demo_label: str
    section_id: str
    section_title: str
    body: str
    source_filename: str


def _parse_meta(block: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for match in _META_LINE_RE.finditer(block):
        key = match.group(1)
        value = match.group(2).strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        meta[key] = value
    required = ("document_id", "title", "version", "demo_label")
    missing = [key for key in required if key not in meta or not meta[key]]
    if missing:
        raise ValueError(f"Policy front matter missing fields: {missing}")
    return meta


def _parse_sections(body: str, *, meta: dict[str, str], filename: str) -> list[PolicySection]:
    matches = list(_SECTION_RE.finditer(body))
    if not matches:
        raise ValueError(f"No sections found in policy file {filename}")

    sections: list[PolicySection] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        chunk = body[start:end].strip()
        lines = chunk.splitlines()
        section_title = match.group(1)
        content_start = 0
        if lines and lines[0].startswith("###"):
            section_title = lines[0].lstrip("#").strip()
            content_start = 1
        section_body = "\n".join(lines[content_start:]).strip()
        if not section_body:
            raise ValueError(
                f"Empty body for section {match.group(1)!r} in {filename}"
            )
        sections.append(
            PolicySection(
                document_id=meta["document_id"],
                title=meta["title"],
                version=meta["version"],
                demo_label=meta["demo_label"],
                section_id=match.group(1),
                section_title=section_title,
                body=section_body,
                source_filename=filename,
            )
        )
    return sections


def parse_policy_markdown(text: str, *, filename: str) -> list[PolicySection]:
    stripped = text.strip()
    match = _FRONT_MATTER_RE.match(stripped)
    if not match:
        raise ValueError(f"Policy file {filename} must start with YAML-like front matter")
    meta = _parse_meta(match.group(1))
    return _parse_sections(match.group(2), meta=meta, filename=filename)


def load_policy_sections_from_dir(directory: Path | None = None) -> list[PolicySection]:
    """Load all ``*.md`` policy files from the fixed directory (sorted by name)."""
    root = directory if directory is not None else POLICY_DOCS_DIR
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Policy docs directory missing: {root}")

    # Safety: only read *.md directly in this directory (no recursion, no user paths).
    files = sorted(path for path in root.iterdir() if path.is_file() and path.suffix == ".md")
    if not files:
        raise FileNotFoundError(f"No policy Markdown files in {root}")

    sections: list[PolicySection] = []
    for path in files:
        # Reject path escape attempts if a caller passes a weird directory.
        if path.parent.resolve() != root:
            continue
        text = path.read_text(encoding="utf-8")
        sections.extend(parse_policy_markdown(text, filename=path.name))
    return sections


@lru_cache(maxsize=1)
def get_policy_sections() -> tuple[PolicySection, ...]:
    return tuple(load_policy_sections_from_dir())


def clear_policy_cache() -> None:
    get_policy_sections.cache_clear()
