#!/usr/bin/env python3

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


def read_journal_content(file_path: Path) -> Optional[str]:
    """Safely read journal content from file."""
    try:
        return file_path.read_text()
    except Exception as e:
        print(f"Error reading {file_path}: {str(e)}")
        return None


def get_journal_dir() -> str:
    """Get journal directory from environment variable."""
    journal_dir = os.getenv("LOGSEQ_JOURNAL_DIR")
    if journal_dir is None:
        raise EnvironmentError(
            "LOGSEQ_JOURNAL_DIR environment variable is not set. "
            "Please set it to the path of your Logseq journal directory."
        )
    return str(Path(journal_dir).expanduser())


def get_week_dates(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> List[datetime]:
    """Get dates between start and end dates, or work week (Monday to Friday) if not specified."""
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            days_diff = (end - start).days + 1
            return [start + timedelta(days=i) for i in range(days_diff)]
        except ValueError as e:
            print(f"Error parsing dates: {e}")
            print("Using default date range (Monday to Friday of current week)")

    # Default: Monday to Friday of current week
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return [monday + timedelta(days=i) for i in range(5)]


def find_journal_files(
    dates: List[datetime], journal_dir: Optional[str] = None
) -> Dict[str, Path]:
    """Find journal files corresponding to the given dates."""
    journal_files = {}

    for date in dates:
        file_path = find_journal_file(date, journal_dir)
        if file_path:
            journal_files[date.strftime("%Y-%m-%d")] = file_path

    return journal_files


def find_journal_file(
    date: datetime, journal_dir: Optional[str] = None
) -> Optional[Path]:
    """Find journal file for the given date."""
    journal_path = Path(journal_dir or get_journal_dir())
    date_str = date.strftime("%Y-%m-%d")
    date_str_underscore = date_str.replace("-", "_")

    patterns = [
        f"{date_str}.md",
        f"{date_str_underscore}.md",
        f"journal_{date_str}.md",
        f"{date_str}_journal.md",
    ]

    for pattern in patterns:
        file_path = journal_path / pattern
        if file_path.exists():
            return file_path

    return None


def parse_date(date_str: Optional[str] = None) -> datetime:
    """Parse date string or return today's date."""
    if not date_str:
        return datetime.now()

    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        print(f"Error parsing date: {e}")
        return datetime.now()
