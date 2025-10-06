#!/usr/bin/env python3
"""
Snipd Export Splitter

This script splits a large Snipd markdown export file into separate files
based on show names. It handles deduplication by only adding new episodes
to existing show files. These files are then used to import the shows into Logseq.

Usage:
    python snipd_splitter.py <input_file> [output_directory]
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set
from datetime import datetime

# Import shared utilities from project root by adding parent to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils import sanitize_filename, safe_file_write, safe_file_append, format_current_timestamp  # noqa: E402


class SnipdEpisode:
    """Represents a single episode from the Snipd export."""

    def __init__(self, title: str, show: str, content: str, episode_link: str = None,
                 host: str = None, thumbnail_url: str = None, publish_date: str = None):
        self.title = title
        self.show = show
        self.content = content
        self.episode_link = episode_link
        self.host = host
        self.thumbnail_url = thumbnail_url
        self.publish_date = publish_date

    def __repr__(self):
        return f"SnipdEpisode(title='{self.title[:50]}...', show='{self.show}')"


class ShowMetadata:
    """Represents show-level metadata for Logseq."""

    def __init__(self, show_name: str, host: str = None, thumbnail_url: str = None):
        self.show_name = show_name
        self.host = host
        self.thumbnail_url = thumbnail_url
        self.episode_count = 0
        self.last_episode_date = None

    def to_logseq_properties(self) -> str:
        """Generate Logseq property block for the show."""
        props = [
            "type:: podcast",
            f"show:: {self.show_name}",
        ]

        if self.host:
            props.append(f"host:: {self.host}")
        if self.thumbnail_url:
            props.append(f"thumbnail:: {self.thumbnail_url}")

        props.append(f"episode-count:: {self.episode_count}")

        if self.last_episode_date:
            props.append(f"last-episode-date:: {self.last_episode_date}")

        return '\n'.join(props) + '\n'


class SnipdSplitter:
    """Main class for splitting Snipd exports."""

    # Regex patterns as class constants for better maintainability
    EPISODE_HEADER_PATTERN = r'^- ## \[\['
    EPISODE_TITLE_PATTERN = r'^- ## \[\[(.+?)\]\]'
    EPISODE_TITLE_PLAIN_PATTERN = r'^- ## ([^[].+?)$'

    # Metadata patterns
    SHOW_PATTERN = r'\s*show:: \[\[(.+?)\]\]'
    EPISODE_LINK_PATTERN = r'\s*episode-link:: \[Open in Snipd\]\((.+?)\)'
    HOST_PATTERN = r'\s*host:: \[\[(.+?)\]\]'
    PUBLISH_DATE_PATTERN = r'\s*publish-date:: \[\[(.+?)\]\]'
    THUMBNAIL_PATTERN = r'\s*!\[Image\]\((.+?)\)'

    # Content transformation patterns
    REMOVE_TITLE_BRACKETS_PATTERN = r'^- ## \[\[(.+?)\]\]'
    REMOVE_SHOW_METADATA_PATTERN = r'^\s*show:: \[\[.+?\]\]\s*$'
    REMOVE_HOST_METADATA_PATTERN = r'^\s*host:: \[\[.+?\]\]\s*$'
    REMOVE_THUMBNAIL_PATTERN = r'^\s*!\[Image\]\(.+?\)\{.+?\}\s*$'
    FIX_PUBLISH_DATE_PATTERN = r'(\s*publish-date:: )\[\[(.+?)\]\]'

    # Show notes and formatting patterns
    SHOW_NOTES_START = "- ### Show notes"
    SHOW_NOTES_END = "#+END_QUOTE"
    TRANSCRIPT_MARKER = "**📚 Transcript**"
    COLLAPSED_PRESERVE_MARKER = "PRESERVE_COLLAPSED"

    # File sanitization pattern
    INVALID_FILENAME_CHARS = r'[<>:"/\\|?*]'
    PARENTHESES_PATTERN = r'[()]'

    def __init__(self, input_file: str, output_dir: str = None):
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir) if output_dir else self.input_file.parent / "split_episodes"
        self.output_dir.mkdir(exist_ok=True)

    def parse_episodes(self) -> List[SnipdEpisode]:
        """Parse episodes from the input markdown file."""
        print(f"📖 Reading episodes from {self.input_file}")

        with open(self.input_file, 'r', encoding='utf-8') as file:
            content = file.read()

        # Split by episode headers using class constant
        episode_parts = re.split(self.EPISODE_HEADER_PATTERN, content, flags=re.MULTILINE)

        episodes = []

        # Skip the first part (before any episode header)
        for i, part in enumerate(episode_parts[1:], 1):
            episode = self._parse_single_episode(f"- ## [[{part}")
            if episode:
                episodes.append(episode)
                if i % 10 == 0:
                    print(f"   Parsed {i} episodes...")

        print(f"✅ Parsed {len(episodes)} episodes total")
        return episodes

    def _extract_episode_title(self, first_line: str) -> str:
        """Extract episode title from the first line."""
        title_match = re.match(self.EPISODE_TITLE_PATTERN, first_line)
        return title_match.group(1) if title_match else None

    def _extract_metadata_from_lines(self, lines: List[str]) -> Dict[str, str]:
        """Extract metadata from episode lines."""
        metadata = {}

        for line in lines[1:15]:  # Check first 15 lines for metadata
            # Use extracted patterns for cleaner code
            patterns = {
                'show': self.SHOW_PATTERN,
                'episode_link': self.EPISODE_LINK_PATTERN,
                'host': self.HOST_PATTERN,
                'publish_date': self.PUBLISH_DATE_PATTERN,
                'thumbnail_url': self.THUMBNAIL_PATTERN
            }

            for key, pattern in patterns.items():
                if key not in metadata:  # Only capture first occurrence
                    match = re.match(pattern, line)
                    if match:
                        metadata[key] = match.group(1)

        return metadata

    def _parse_single_episode(self, episode_text: str) -> SnipdEpisode:
        """Parse a single episode from its text content."""
        lines = episode_text.split('\n')

        # Extract title
        title = self._extract_episode_title(lines[0])
        if not title:
            return None

        # Extract metadata
        metadata = self._extract_metadata_from_lines(lines)

        if not metadata.get('show'):
            print(f"⚠️  Warning: No show found for episode '{title[:50]}...'")
            return None

        return SnipdEpisode(
            title=title,
            show=metadata.get('show'),
            content=episode_text,
            episode_link=metadata.get('episode_link'),
            host=metadata.get('host'),
            thumbnail_url=metadata.get('thumbnail_url'),
            publish_date=metadata.get('publish_date')
        )

    def _remove_episode_title_brackets(self, content: str) -> str:
        """Remove double brackets from episode titles."""
        return re.sub(
            self.REMOVE_TITLE_BRACKETS_PATTERN,
            r'- ## \1',
            content,
            flags=re.MULTILINE
        )

    def _remove_show_level_metadata(self, content: str) -> str:
        """Remove show-level metadata lines completely."""
        patterns = [
            self.REMOVE_SHOW_METADATA_PATTERN,
            self.REMOVE_HOST_METADATA_PATTERN,
            self.REMOVE_THUMBNAIL_PATTERN
        ]

        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.MULTILINE)

        return content

    def _fix_publish_date_format(self, content: str) -> str:
        """Transform publish-date format from [[date]] to date."""
        return re.sub(self.FIX_PUBLISH_DATE_PATTERN, r'\1\2', content)

    def _clean_up_formatting(self, content: str) -> str:
        """Clean up formatting and spacing."""
        # Clean up multiple consecutive empty lines
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Ensure proper line breaks and indentation
        formatting_fixes = [
            (r'(- ## [^\n]+)\s+(episode-link::)', r'\1\n  \2'),
            (r'(episode-link:: [^\n]+)\s+(publish-date::)', r'\1\n  \2'),
            (r'(publish-date:: [^\n]+)\s+(- ###)', r'\1\n\2')
        ]

        for pattern, replacement in formatting_fixes:
            content = re.sub(pattern, replacement, content)

        return content

    def _remove_show_notes_section(self, content: str) -> str:
        """Remove the 'Show notes' section entirely."""
        while self.SHOW_NOTES_START in content:
            start_idx = content.find(self.SHOW_NOTES_START)
            if start_idx == -1:
                break

            end_idx = content.find(self.SHOW_NOTES_END, start_idx)
            if end_idx == -1:
                break

            # Include the end marker and following whitespace
            end_idx = content.find('\n', end_idx + len(self.SHOW_NOTES_END))
            if end_idx != -1:
                while end_idx < len(content) and content[end_idx] in '\n\t ':
                    end_idx += 1
            else:
                end_idx = len(content)

            content = content[:start_idx] + content[end_idx:]

        return content

    def _handle_collapsed_sections(self, content: str) -> str:
        """Handle collapsed:: true sections, preserving only transcript ones."""
        # Preserve transcript collapsed lines
        content = re.sub(
            rf'(\*\*📚 Transcript\*\*\s*\n\s*)(collapsed:: true)',
            rf'\1{self.COLLAPSED_PRESERVE_MARKER}',
            content,
            flags=re.MULTILINE
        )

        # Remove all other collapsed:: true lines
        content = re.sub(r'\s*collapsed:: true\s*\n', '\n', content, flags=re.MULTILINE)

        # Restore preserved transcript collapsed lines
        content = content.replace(self.COLLAPSED_PRESERVE_MARKER, 'collapsed:: true')

        return content

    def _format_transcript_content(self, content: str) -> str:
        """Fix transcript content indentation."""
        lines = content.split('\n')
        result_lines = []
        inside_transcript = False
        transcript_base_indent = 0

        for line in lines:
            if self.TRANSCRIPT_MARKER in line:
                inside_transcript = True
                transcript_base_indent = len(line) - len(line.lstrip())
                result_lines.append(line)
            elif inside_transcript:
                current_indent = len(line) - len(line.lstrip()) if line.strip() else 0

                # End transcript section if we hit a header at same or lesser indent
                if (line.strip() and
                    current_indent <= transcript_base_indent and
                    any(marker in line for marker in ['####', '###', '##', '- ####'])):
                    inside_transcript = False
                    result_lines.append(line)
                elif line.strip():  # Non-empty line inside transcript
                    result_lines.append(self._format_transcript_line(line, transcript_base_indent))
                else:
                    result_lines.append(line)
            else:
                result_lines.append(line)

        return '\n'.join(result_lines)

    def _format_transcript_line(self, line: str, base_indent: int) -> str:
        """Format individual transcript lines with proper indentation."""
        stripped = line.strip()
        extra_indent = base_indent + 2

        if stripped.startswith('#+BEGIN_QUOTE') or stripped.startswith('#+END_QUOTE'):
            return ' ' * extra_indent + '- ' + stripped
        elif stripped.startswith('**') and stripped.endswith('**'):
            return ' ' * (extra_indent + 2) + stripped
        else:
            return ' ' * (extra_indent + 2) + stripped

    def _transform_episode_to_namespace(self, episode: SnipdEpisode) -> str:
        """Transform episode content by removing show-level metadata and cleaning up format."""
        content = episode.content

        # Apply transformations in sequence using extracted methods
        content = self._remove_episode_title_brackets(content)
        content = self._remove_show_level_metadata(content)
        content = self._fix_publish_date_format(content)
        content = self._clean_up_formatting(content)
        content = self._remove_show_notes_section(content)
        content = self._handle_collapsed_sections(content)
        content = self._format_transcript_content(content)

        return content

    def group_by_show(self, episodes: List[SnipdEpisode]) -> Tuple[Dict[str, List[SnipdEpisode]], Dict[str, ShowMetadata]]:
        """Group episodes by show name and collect show metadata."""
        print(f"📂 Grouping episodes by show...")

        shows = {}
        show_metadata = {}

        for episode in episodes:
            if episode.show not in shows:
                shows[episode.show] = []
                # Create show metadata from first episode of the show
                show_metadata[episode.show] = ShowMetadata(
                    show_name=episode.show,
                    host=episode.host,
                    thumbnail_url=episode.thumbnail_url
                )
            shows[episode.show].append(episode)

        # Update episode counts and last episode date
        for show_name, eps in shows.items():
            show_metadata[show_name].episode_count = len(eps)
            # Find the episode with the latest publish date
            if eps:
                latest_episode = max(eps, key=lambda ep: ep.publish_date or "0000-00-00")
                show_metadata[show_name].last_episode_date = latest_episode.publish_date

        print(f"✅ Found {len(shows)} unique shows:")
        for show, eps in shows.items():
            print(f"   • {show}: {len(eps)} episodes")

        return shows, show_metadata


    def _get_existing_episode_titles(self, file_path: Path) -> Set[str]:
        """Extract episode titles from an existing show file."""
        if not file_path.exists():
            return set()

        titles = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                # Find episode titles with brackets (old format)
                bracketed_titles = re.findall(self.EPISODE_TITLE_PATTERN, content, re.MULTILINE)
                titles.update(title.strip() for title in bracketed_titles)

                # Find episode titles without brackets (new format)
                plain_titles = re.findall(self.EPISODE_TITLE_PLAIN_PATTERN, content, re.MULTILINE)
                titles.update(title.strip() for title in plain_titles)

        except Exception as e:
            print(f"⚠️  Warning: Could not read existing file {file_path}: {e}")

        return titles



    def _format_timestamp(self) -> str:
        """Get current timestamp for logging."""
        return format_current_timestamp()

    def _prepare_episode_content(self, episodes: List[SnipdEpisode]) -> str:
        """Transform episodes to content string."""
        content_parts = []
        for episode in episodes:
            transformed_content = self._transform_episode_to_namespace(episode)
            content_parts.append(transformed_content)
            if not transformed_content.endswith('\n'):
                content_parts.append('\n')
        return ''.join(content_parts)

    def _update_existing_show_file(self, file_path: Path, new_episodes: List[SnipdEpisode], show_name: str, filename: str) -> bool:
        """Update an existing show file with new episodes."""
        if not new_episodes:
            print(f"   📄 {show_name}: No new episodes to add")
            return True

        timestamp_header = f"\n<!-- New episodes added on {format_current_timestamp()} -->\n"
        new_content = timestamp_header + self._prepare_episode_content(new_episodes)

        if safe_file_append(file_path, new_content):
            print(f"   ✅ Updated {filename}: {len(new_episodes)} new episodes")
            return True
        return False

    def _create_new_show_file(self, file_path: Path, episodes: List[SnipdEpisode], metadata: ShowMetadata, filename: str) -> bool:
        """Create a new show file with metadata and episodes."""
        content_parts = [
            metadata.to_logseq_properties(),
            '\n',
            "<!-- Episodes exported from Snipd -->\n\n",
            self._prepare_episode_content(episodes)
        ]

        if safe_file_write(file_path, ''.join(content_parts)):
            print(f"   ✅ Created {filename}: {len(episodes)} episodes with Logseq metadata")
            return True
        return False

    def write_show_files(self, shows: Dict[str, List[SnipdEpisode]], show_metadata: Dict[str, ShowMetadata]):
        """Write separate markdown files for each show with Logseq metadata headers."""
        print(f"📝 Writing show files to {self.output_dir}")

        for show_name, episodes in shows.items():
            filename = f"{sanitize_filename(show_name)}.md"
            file_path = self.output_dir / filename

            # Get existing episodes to avoid duplicates
            existing_titles = self._get_existing_episode_titles(file_path)
            new_episodes = [ep for ep in episodes if ep.title not in existing_titles]
            metadata = show_metadata[show_name]

            # Use helper methods for cleaner code
            if file_path.exists():
                self._update_existing_show_file(file_path, new_episodes, show_name, filename)
            else:
                self._create_new_show_file(file_path, episodes, metadata, filename)

    def run(self):
        """Execute the full splitting process."""
        print(f"🚀 Starting Snipd export splitting...")
        print(f"   Input: {self.input_file}")
        print(f"   Output directory: {self.output_dir}\n")

        # Parse episodes
        episodes = self.parse_episodes()
        if not episodes:
            print("❌ No episodes found!")
            return

        print()

        # Group by show and collect metadata
        shows, show_metadata = self.group_by_show(episodes)
        print()

        # Write files with metadata
        self.write_show_files(shows, show_metadata)

        print(f"\n🎉 Done! Split into {len(shows)} show files in {self.output_dir}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python snipd_splitter.py <input_file> [output_directory]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)

    splitter = SnipdSplitter(input_file, output_dir)
    splitter.run()


if __name__ == "__main__":
    main()
