#!/usr/bin/env python3
"""Convert Markdown into a Logseq-style outline (headings and paragraphs only)."""

from __future__ import annotations

import argparse
import re
import sys
from typing import List, Optional, Tuple


Heading = Tuple[int, str]  # (level, text)


ATX_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.*?)\s*(?P<trailing>#+\s*)?$")

from utils import parse_atx_heading, is_setext_underline, make_indent


def parse_markdown_blocks(
    markdown_text: str,
    paragraph_mode: str = "lines",
) -> List[Tuple[str, Optional[int], str]]:
    """Parse markdown into a sequence of blocks.

    Returns a list of tuples: (kind, level, text)
    - kind: "heading" or "paragraph"
    - level: heading level for headings (1..6), or None for paragraphs
    - text: the content

    The parser supports:
    - ATX headings (e.g., "## Title")
    - Setext headings (e.g., "Title" followed by "=====")
    - Paragraphs:
      - paragraph_mode == "lines": each non-empty line becomes a paragraph block
      - paragraph_mode == "blocks": groups of non-empty lines become a single paragraph
    """
    lines = markdown_text.splitlines()
    blocks: List[Tuple[str, Optional[int], str]] = []
    i = 0
    pending_paragraph_lines: List[str] = []

    def flush_paragraph() -> None:
        nonlocal pending_paragraph_lines
        if pending_paragraph_lines:
            paragraph_text = " ".join(
                line.strip() for line in pending_paragraph_lines if line.strip()
            )
            if paragraph_text:
                blocks.append(("paragraph", None, paragraph_text))
            pending_paragraph_lines = []

    while i < len(lines):
        line = lines[i]

        # Blank line ends a paragraph in blocks mode; in lines mode, just skip
        if not line.strip():
            if paragraph_mode == "blocks":
                flush_paragraph()
            i += 1
            continue

        # ATX heading (e.g., #, ##, ..., ######)
        atx = parse_atx_heading(line)
        if atx:
            if paragraph_mode == "blocks":
                flush_paragraph()
            level, text = atx
            blocks.append(("heading", level, text))
            i += 1
            continue

        # Setext headings support: a non-empty line followed by ===... (H1) or ---... (H2)
        if i + 1 < len(lines):
            underline = lines[i + 1]
            setext_level = is_setext_underline(underline)
            if setext_level:
                if paragraph_mode == "blocks":
                    flush_paragraph()
                blocks.append(("heading", setext_level, line.strip()))
                i += 2
                continue

        # Otherwise, part of a paragraph
        if paragraph_mode == "lines":
            # Each non-empty line is its own paragraph block
            blocks.append(("paragraph", None, line.strip()))
            i += 1
        else:
            pending_paragraph_lines.append(line)
            i += 1

    # Flush any remaining paragraph
    flush_paragraph()
    return blocks


def convert_to_logseq_outline(markdown_text: str, paragraph_mode: str = "lines") -> str:
    """Convert parsed markdown blocks to a Logseq-style outline string.

    Rules:
    - Heading level n becomes a bullet at indent (n - 1), content: "#"*n + " " + text
    - Paragraph becomes a bullet at indent (current_heading_level or 0 if none)
    - Indent uses two spaces per level
    """
    blocks = parse_markdown_blocks(markdown_text, paragraph_mode=paragraph_mode)
    outline_lines: List[str] = []
    current_heading_level = 0  # 0 means no heading seen yet

    for kind, level, text in blocks:
        if kind == "heading" and level is not None:
            indent_level = max(0, level - 1)
            indent = make_indent(indent_level, width=2)
            outline_lines.append(f"{indent}- {'#' * level} {text}")
            current_heading_level = level
        elif kind == "paragraph":
            base_indent_level = current_heading_level if current_heading_level > 0 else 0
            # Detect Logseq property lines of the form key:: value (no leading dash)
            candidate = text[2:].lstrip() if text.startswith("- ") else text
            if re.match(r"^[A-Za-z0-9_-][A-Za-z0-9 _-]*::", candidate):
                indent = make_indent(base_indent_level, width=2)
                outline_lines.append(f"{indent}{candidate}")
            elif text.startswith("- "):
                # If the source line already looks like a bullet, avoid creating "- -".
                # Under a heading, treat it as a child bullet (deepen one level); at root, keep top level.
                adjusted_indent_level = base_indent_level + (1 if base_indent_level > 0 else 0)
                indent = make_indent(adjusted_indent_level, width=2)
                outline_lines.append(f"{indent}- {candidate}")
            else:
                indent = make_indent(base_indent_level, width=2)
                outline_lines.append(f"{indent}- {text}")
        else:
            # Fallback safety: treat unknown as a top-level paragraph
            outline_lines.append(f"- {text}")

    return "\n".join(outline_lines) + ("\n" if outline_lines else "")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert longform Markdown into Logseq-style outline (headings + paragraphs)."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Input Markdown file path. If omitted, reads from stdin.",
    )
    parser.add_argument(
        "--paragraph-mode",
        choices=("lines", "blocks"),
        default="lines",
        help=(
            "How to treat paragraph lines: 'lines' makes each line a bullet (default), "
            "'blocks' groups consecutive lines (separated by blanks) into one bullet."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path. If omitted, writes to stdout.",
    )

    args = parser.parse_args(argv)

    # Read input
    try:
        if args.input:
            with open(args.input, "r", encoding="utf-8") as f:
                input_text = f.read()
        else:
            input_text = sys.stdin.read()
    except OSError as exc:
        print(f"Error reading input: {exc}", file=sys.stderr)
        return 1

    output_text = convert_to_logseq_outline(
        input_text, paragraph_mode=args.paragraph_mode
    )

    # Write output
    try:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_text)
        else:
            sys.stdout.write(output_text)
    except OSError as exc:
        print(f"Error writing output: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


