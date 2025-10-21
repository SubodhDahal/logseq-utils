#!/usr/bin/env python3
"""Convert Markdown into a Logseq-style outline (headings and paragraphs only)."""

from __future__ import annotations

import argparse
import re
import sys
from typing import List, Optional, Tuple


Heading = Tuple[int, str]  # (level, text)


ATX_HEADING_RE = re.compile(
    r"^(?P<hashes>#{1,6})\s+(?P<text>.*?)\s*(?P<trailing>#+\s*)?$"
)

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
    - ATX headings with leading bullets (e.g., "- ## Title")
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

        # Check for ATX heading with optional leading bullet
        stripped_line = line.strip()
        if stripped_line.startswith("- "):
            candidate_heading = stripped_line[2:].strip()
        else:
            candidate_heading = stripped_line

        atx = parse_atx_heading(candidate_heading)
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
                blocks.append(("heading", setext_level, stripped_line))
                i += 2
                continue

        # Otherwise, part of a paragraph
        if paragraph_mode == "lines":
            # Each non-empty line is its own paragraph block
            blocks.append(("paragraph", None, stripped_line))
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
    - Paragraph becomes a bullet at indent (current_heading_level), making it a child of the heading
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
            # Content under a heading should be indented as a child of that heading
            # This means using the heading's indentation level + 1
            if current_heading_level > 0:
                # Heading is at level (current_heading_level - 1), so content goes at current_heading_level
                base_indent_level = current_heading_level
            else:
                # No heading seen yet, place at root level
                base_indent_level = 0

            # Detect Logseq property lines of the form key:: value (no leading dash)
            candidate = text[2:].lstrip() if text.startswith("- ") else text
            if re.match(r"^[A-Za-z0-9_-][A-Za-z0-9 _-]*::", candidate):
                indent = make_indent(base_indent_level, width=2)
                outline_lines.append(f"{indent}{candidate}")
            else:
                # For all other content (including existing bullets), treat as child content
                indent = make_indent(base_indent_level, width=2)
                outline_lines.append(f"{indent}- {candidate}")
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
    parser.add_argument(
        "-i",
        "--in-place",
        action="store_true",
        help="Overwrite the input file with converted output (requires an input path).",
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

    # Validate conflicting options
    if args.in_place and args.output:
        print(
            "Cannot use --in-place with --output. Choose one destination.",
            file=sys.stderr,
        )
        return 2

    # Write output
    try:
        if args.in_place:
            if not args.input:
                print("--in-place requires an input file path.", file=sys.stderr)
                return 2
            with open(args.input, "w", encoding="utf-8") as f:
                f.write(output_text)
        elif args.output:
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
