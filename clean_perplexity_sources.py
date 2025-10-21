#!/usr/bin/env python3
"""Clean Perplexity source links from text content.

This script removes source citations that Perplexity adds to its output,
such as [source_name](url) and [source_name+number](url) patterns.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional, List


def clean_perplexity_sources(text: str) -> str:
    """Remove Perplexity source links from text.

    Removes patterns like:
    - [autoscout24+2](https://www.autoscout24.de/...)
    - [weinrank](http://www.weinrank.de/...)
    - [fahrschule-braun](https://www.fahrschule-braun.info/...)
    - And other similar source citation patterns

    Args:
        text: Input text containing source links

    Returns:
        Cleaned text with source links removed
    """
    # Pattern to match Perplexity source links
    # Matches: [source_name](url) or [source_name+number](url)
    source_link_pattern = re.compile(
        r"\[([a-zA-Z0-9_-]+(?:\+\d+)?)\]\([^)]+\)", re.IGNORECASE
    )

    # Remove the source links
    cleaned_text = source_link_pattern.sub("", text)

    # Clean up any trailing invisible characters or extra spaces
    # Remove zero-width characters and other invisible Unicode characters
    invisible_chars = re.compile(r"[\u200b-\u200f\ufeff\u2060]")
    cleaned_text = invisible_chars.sub("", cleaned_text)

    # Clean up multiple spaces and trailing spaces at end of lines
    cleaned_text = re.sub(r" +", " ", cleaned_text)  # Multiple spaces to single space
    cleaned_text = re.sub(
        r" +$", "", cleaned_text, flags=re.MULTILINE
    )  # Trailing spaces

    return cleaned_text


def process_file(
    input_path: Path, output_path: Optional[Path] = None, in_place: bool = False
) -> bool:
    """Process a file to clean Perplexity sources.

    Args:
        input_path: Path to input file
        output_path: Path to output file (if None, prints to stdout)
        in_place: If True, overwrites the input file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Read input file
        with input_path.open("r", encoding="utf-8") as f:
            content = f.read()

        # Clean the content
        cleaned_content = clean_perplexity_sources(content)

        # Write output
        if in_place:
            with input_path.open("w", encoding="utf-8") as f:
                f.write(cleaned_content)
            print(f"✅ Cleaned sources in {input_path}", file=sys.stderr)
        elif output_path:
            with output_path.open("w", encoding="utf-8") as f:
                f.write(cleaned_content)
            print(f"✅ Cleaned content written to {output_path}", file=sys.stderr)
        else:
            sys.stdout.write(cleaned_content)

        return True

    except Exception as e:
        print(f"❌ Error processing {input_path}: {e}", file=sys.stderr)
        return False


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean Perplexity source links from text files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.md                    # Print cleaned content to stdout
  %(prog)s input.md -o output.md       # Write cleaned content to output.md
  %(prog)s input.md -i                 # Clean in-place (overwrite input.md)
  cat input.md | %(prog)s              # Process stdin to stdout
        """,
    )

    parser.add_argument(
        "input", nargs="?", help="Input file path. If omitted, reads from stdin."
    )

    parser.add_argument(
        "-o", "--output", help="Output file path. If omitted, writes to stdout."
    )

    parser.add_argument(
        "-i",
        "--in-place",
        action="store_true",
        help="Overwrite the input file with cleaned content (requires input file).",
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview the changes without writing (shows before/after).",
    )

    args = parser.parse_args(argv)

    # Validate conflicting options
    if args.in_place and args.output:
        print("❌ Cannot use --in-place with --output. Choose one.", file=sys.stderr)
        return 2

    if args.in_place and not args.input:
        print("❌ --in-place requires an input file path.", file=sys.stderr)
        return 2

    try:
        # Read input
        if args.input:
            input_path = Path(args.input)
            if not input_path.exists():
                print(f"❌ Input file not found: {input_path}", file=sys.stderr)
                return 1
            with input_path.open("r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = sys.stdin.read()
            input_path = None

        # Clean the content
        cleaned_content = clean_perplexity_sources(content)

        # Preview mode
        if args.preview:
            if content != cleaned_content:
                print("📋 Changes preview:", file=sys.stderr)
                print("=" * 50, file=sys.stderr)

                # Show a diff-like preview
                original_lines = content.splitlines()
                cleaned_lines = cleaned_content.splitlines()

                for i, (orig, clean) in enumerate(
                    zip(original_lines, cleaned_lines), 1
                ):
                    if orig != clean:
                        print(f"Line {i}:", file=sys.stderr)
                        print(f"  - {orig}", file=sys.stderr)
                        print(f"  + {clean}", file=sys.stderr)
                        print(file=sys.stderr)

                print("=" * 50, file=sys.stderr)
                print(
                    f"✅ Would remove source links from {len(original_lines)} lines",
                    file=sys.stderr,
                )
            else:
                print("✅ No source links found to clean", file=sys.stderr)
            return 0

        # Process normally
        if input_path:
            output_path = Path(args.output) if args.output else None
            success = process_file(input_path, output_path, args.in_place)
            return 0 if success else 1
        else:
            # Stdin input
            if args.output:
                with Path(args.output).open("w", encoding="utf-8") as f:
                    f.write(cleaned_content)
                print(f"✅ Cleaned content written to {args.output}", file=sys.stderr)
            else:
                sys.stdout.write(cleaned_content)
            return 0

    except KeyboardInterrupt:
        print("\n❌ Interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
