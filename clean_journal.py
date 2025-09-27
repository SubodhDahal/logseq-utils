#!/usr/bin/env python3
"""
Journal Cleaner Script

This script cleans journal entries by removing empty sections.
It can process a specific date's journal or all journals within a date range.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple, Dict

from utils import (
    find_journal_file,
    find_journal_files,
    parse_date,
    read_journal_content,
)

# ---- Data Structures ----

@dataclass
class Section:
    """Represents a section in the journal."""
    heading: str  # The section heading line
    indent_level: int  # Indentation level of the heading
    content: List[Tuple[str, int]]  # List of (line, indent_level) pairs


# ---- CLI Argument Handling ----

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Clean journal entries by removing empty sections"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Clean a specific date in YYYY-MM-DD format (default: clean all entries older than today)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Clean all journal entries including today's (default: skip today's entry)",
    )
    return parser.parse_args()


# ---- File Selection Logic ----

def get_journal_files_to_clean(args: argparse.Namespace) -> List[Path]:
    """
    Get list of journal files to clean based on arguments.

    Args:
        args: Command line arguments

    Returns:
        List of Path objects for journal files to be cleaned
    """
    # Case 1: Clean a specific date's journal
    if args.date:
        date = parse_date(args.date)
        journal_file = find_journal_file(date)
        return [journal_file] if journal_file else []

    # Case 2: Clean multiple journals based on date range
    today = datetime.now().date()

    # Generate dates for the past year
    dates = []
    start_date = today - timedelta(days=365)
    while start_date <= today:
        dates.append(start_date)
        start_date += timedelta(days=1)

    # Get journal files with their corresponding dates
    journal_files_dict = find_journal_files(dates)

    # Filter out today's file unless --all flag is specified
    if not args.all:
        journal_files_dict = filter_out_today_and_future(journal_files_dict, today)

    return list(journal_files_dict.values())


def filter_out_today_and_future(
    journal_files_dict: Dict[str, Path], today: datetime.date
) -> Dict[str, Path]:
    """
    Filter out today's file and any future files.

    Args:
        journal_files_dict: Dictionary mapping date strings to file paths
        today: Today's date for comparison

    Returns:
        Filtered dictionary with only past dates
    """
    return {
        date_str: file_path
        for date_str, file_path in journal_files_dict.items()
        if parse_date(date_str).date() < today
    }


# ---- Section Parsing and Analysis ----

def get_indentation_level(line: str) -> int:
    """Get the indentation level of a line (number of leading tabs/spaces)."""
    return len(line) - len(line.lstrip())


def is_section_heading(line: str) -> bool:
    """
    Check if a line is a section heading (starts with ## or - ##).

    Args:
        line: The line to check

    Returns:
        True if the line is a section heading, False otherwise
    """
    stripped = line.strip()
    # Handle bullet point headings (- ##)
    if stripped.startswith("- ##"):
        stripped = stripped[2:]
    return stripped.startswith("##")


def has_nested_content(section: Section) -> bool:
    """
    Check if a section has any meaningful content (not just headings).

    A section is considered to have meaningful content if it contains
    at least one non-heading line at a deeper indentation level than
    the section heading.

    Args:
        section: The section to check

    Returns:
        True if the section has meaningful content, False otherwise
    """
    has_content = False
    has_only_headings = True

    for line, indent in section.content:
        stripped = line.strip()
        # Skip empty lines
        if not stripped:
            continue

        # Check if line is at a deeper indentation level
        if indent > section.indent_level:
            has_content = True

            # Check if it's not just a heading
            if not is_section_heading(line):
                has_only_headings = False
                break

    # Return True only if there's content and it's not just headings
    return has_content and not has_only_headings


# ---- Content Cleaning Logic ----

def process_section(section: Section, cleaned_lines: List[str]) -> None:
    """
    Process a section and add its content to cleaned_lines if not empty.

    Args:
        section: The section to process
        cleaned_lines: List to append cleaned content to
    """
    if has_nested_content(section):
        # Keep the section and all its content if it has meaningful nested content
        cleaned_lines.append(section.heading)
        cleaned_lines.extend(line for line, _ in section.content)
    else:
        # If section is empty but has content at lesser indentation,
        # keep only the lesser indented content
        cleaned_lines.extend(
            line for line, indent in section.content if indent <= section.indent_level
        )


def clean_journal_content(content: str) -> str:
    """
    Clean journal content by removing empty sections.

    This function parses the journal content line by line, identifies sections,
    and removes sections that don't have meaningful content.

    Args:
        content: The journal content as a string

    Returns:
        Cleaned journal content as a string
    """
    lines = content.split("\n")
    cleaned_lines: List[str] = []
    current_section: Optional[Section] = None

    for line in lines:
        indent_level = get_indentation_level(line)

        if is_section_heading(line):
            # Process previous section if exists
            if current_section:
                process_section(current_section, cleaned_lines)
            # Start new section
            current_section = Section(
                heading=line, indent_level=indent_level, content=[]
            )
        else:
            if current_section:
                if indent_level <= current_section.indent_level:
                    # Content belongs to parent, process current section
                    process_section(current_section, cleaned_lines)
                    cleaned_lines.append(line)
                    current_section = None
                else:
                    # Content belongs to current section
                    current_section.content.append((line, indent_level))
            else:
                # Not in any section, keep the line
                cleaned_lines.append(line)

    # Process the last section if exists
    if current_section:
        process_section(current_section, cleaned_lines)

    return "\n".join(cleaned_lines)


# ---- Main Execution Logic ----

def clean_journal_files(journal_files: List[Path]) -> int:
    """
    Clean the provided journal files.

    Args:
        journal_files: List of journal files to clean

    Returns:
        Number of files that were cleaned
    """
    cleaned_count = 0

    for journal_file in journal_files:
        # Read content
        content = read_journal_content(journal_file)
        if not content:
            continue

        # Clean content
        cleaned_content = clean_journal_content(content)

        # Write back if changed
        if cleaned_content != content:
            try:
                journal_file.write_text(cleaned_content)
                print(f"✓ Cleaned {journal_file.name}")
                cleaned_count += 1
            except Exception as e:
                print(f"✗ Error writing to {journal_file}: {str(e)}")

    return cleaned_count


def main():
    """Main entry point for the script."""
    # Parse arguments and get files to clean
    args = parse_args()
    journal_files = get_journal_files_to_clean(args)

    if not journal_files:
        print("No journal files found to clean.")
        return

    # Display files to be processed
    print(f"\nFound {len(journal_files)} journal files to clean:")
    for file in journal_files:
        print(f"  • {file.name}")
    print()

    # Clean the files
    cleaned_count = clean_journal_files(journal_files)

    # Report results
    if cleaned_count > 0:
        print(f"\nSuccessfully cleaned {cleaned_count} journal files.")
    else:
        print("\nNo empty sections found to clean in any files.")


if __name__ == "__main__":
    main()
