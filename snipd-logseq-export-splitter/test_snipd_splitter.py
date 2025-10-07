#!/usr/bin/env python3
"""
Unit tests for snipd_splitter.py

Run with: python -m pytest test_snipd_splitter.py -v
or: python test_snipd_splitter.py
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open
import sys
import os

# Add the current directory to path so we can import our module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from snipd_splitter import SnipdEpisode, ShowMetadata, SnipdSplitter
from utils import (
    sanitize_filename,
    safe_file_write,
    safe_file_append,
    format_current_timestamp,
)


class TestSnipdEpisode(unittest.TestCase):
    """Test the SnipdEpisode class."""

    def test_episode_creation(self):
        """Test basic episode creation."""
        episode = SnipdEpisode(
            title="Test Episode",
            show="Test Show",
            content="Test content",
            episode_link="https://example.com",
            host="Test Host",
            thumbnail_url="https://example.com/thumb.jpg",
            publish_date="2025-01-01"
        )

        self.assertEqual(episode.title, "Test Episode")
        self.assertEqual(episode.show, "Test Show")
        self.assertEqual(episode.content, "Test content")
        self.assertEqual(episode.episode_link, "https://example.com")
        self.assertEqual(episode.host, "Test Host")
        self.assertEqual(episode.thumbnail_url, "https://example.com/thumb.jpg")
        self.assertEqual(episode.publish_date, "2025-01-01")

    def test_episode_repr(self):
        """Test episode string representation."""
        episode = SnipdEpisode("A very long episode title that should be truncated", "Test Show", "content")
        repr_str = repr(episode)
        self.assertIn("A very long episode title that should be truncated"[:50], repr_str)
        self.assertIn("Test Show", repr_str)


class TestShowMetadata(unittest.TestCase):
    """Test the ShowMetadata class."""

    def test_show_metadata_creation(self):
        """Test basic show metadata creation."""
        metadata = ShowMetadata("Test Show", "Test Host", "https://example.com/thumb.jpg")

        self.assertEqual(metadata.show_name, "Test Show")
        self.assertEqual(metadata.host, "Test Host")
        self.assertEqual(metadata.thumbnail_url, "https://example.com/thumb.jpg")
        self.assertEqual(metadata.episode_count, 0)
        self.assertIsNone(metadata.last_episode_date)

    def test_logseq_properties_basic(self):
        """Test Logseq properties generation with basic data."""
        metadata = ShowMetadata("Test Show")
        metadata.episode_count = 5

        properties = metadata.to_logseq_properties()
        expected_lines = [
            "type:: podcast",
            "show:: Test Show",
            "episode-count:: 5"
        ]

        for line in expected_lines:
            self.assertIn(line, properties)

    def test_logseq_properties_full(self):
        """Test Logseq properties generation with all data."""
        metadata = ShowMetadata("Test Show", "Test Host", "https://example.com/thumb.jpg")
        metadata.episode_count = 10
        metadata.last_episode_date = "2025-01-01"

        properties = metadata.to_logseq_properties()
        expected_lines = [
            "type:: podcast",
            "show:: Test Show",
            "host:: Test Host",
            "thumbnail:: https://example.com/thumb.jpg",
            "episode-count:: 10",
            "last-episode-date:: 2025-01-01"
        ]

        for line in expected_lines:
            self.assertIn(line, properties)


class TestSnipdSplitter(unittest.TestCase):
    """Test the SnipdSplitter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_input_file = Path(self.temp_dir) / "test_input.md"
        self.splitter = SnipdSplitter(str(self.test_input_file), self.temp_dir)

        # Sample episode text for testing
        self.sample_episode_text = """- ## [[Test Episode Title]]
  episode-link:: [Open in Snipd](https://example.com/episode)
  publish-date:: [[2025-01-01]]
  show:: [[Test Show]]
  host:: [[Test Host]]
  ![Image](https://example.com/thumb.jpg)

- ### Summary
  This is a test episode summary.

- ### Show notes
  #+BEGIN_QUOTE
  These are show notes that should be removed.
  #+END_QUOTE

- #### **📚 Transcript**
  collapsed:: true
  - #+BEGIN_QUOTE
    **Speaker 1**
    This is transcript content.
    **Speaker 2**
    More transcript content.
  - #+END_QUOTE
"""

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_extract_episode_title_valid(self):
        """Test extracting valid episode title."""
        title = self.splitter._extract_episode_title("- ## [[Valid Episode Title]]")
        self.assertEqual(title, "Valid Episode Title")

    def test_extract_episode_title_invalid(self):
        """Test extracting invalid episode title."""
        title = self.splitter._extract_episode_title("Not a valid title format")
        self.assertIsNone(title)

    def test_extract_metadata_from_lines(self):
        """Test metadata extraction from lines."""
        lines = [
            "- ## [[Test Episode]]",
            "  show:: [[Test Show]]",
            "  host:: [[Test Host]]",
            "  episode-link:: [Open in Snipd](https://example.com)",
            "  publish-date:: [[2025-01-01]]",
            "  ![Image](https://example.com/thumb.jpg)"
        ]

        metadata = self.splitter._extract_metadata_from_lines(lines)

        self.assertEqual(metadata['show'], "Test Show")
        self.assertEqual(metadata['host'], "Test Host")
        self.assertEqual(metadata['episode_link'], "https://example.com")
        self.assertEqual(metadata['publish_date'], "2025-01-01")
        self.assertEqual(metadata['thumbnail_url'], "https://example.com/thumb.jpg")

    def test_parse_single_episode_valid(self):
        """Test parsing a valid episode."""
        episode = self.splitter._parse_single_episode(self.sample_episode_text)

        self.assertIsNotNone(episode)
        self.assertEqual(episode.title, "Test Episode Title")
        self.assertEqual(episode.show, "Test Show")
        self.assertEqual(episode.host, "Test Host")
        self.assertEqual(episode.episode_link, "https://example.com/episode")
        self.assertEqual(episode.publish_date, "2025-01-01")

    def test_parse_single_episode_no_show(self):
        """Test parsing episode without show information."""
        episode_text = "- ## [[Test Episode]]\n  publish-date:: [[2025-01-01]]"
        episode = self.splitter._parse_single_episode(episode_text)

        self.assertIsNone(episode)

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        result = sanitize_filename("Test Show Name")
        self.assertEqual(result, "Test Show Name")

    def test_sanitize_filename_special_chars(self):
        """Test filename sanitization with special characters."""
        result = sanitize_filename("Test/Show<>Name:?*")
        self.assertEqual(result, "Test-Show--Name")

    def test_sanitize_filename_parentheses(self):
        """Test filename sanitization with parentheses."""
        result = sanitize_filename("Test Show (Podcast)")
        self.assertEqual(result, "Test Show Podcast")

    def test_remove_episode_title_brackets(self):
        """Test removing brackets from episode titles."""
        content = "- ## [[Episode Title]]\n  Some content"
        result = self.splitter._remove_episode_title_brackets(content)
        self.assertIn("- ## Episode Title", result)
        self.assertNotIn("[[", result)

    def test_remove_show_level_metadata(self):
        """Test removing show-level metadata."""
        content = """- ## Episode Title
  show:: [[Test Show]]
  host:: [[Test Host]]
  ![Image](https://example.com/thumb.jpg){height 300, width 400}
  episode-link:: [Link](https://example.com)"""

        result = self.splitter._remove_show_level_metadata(content)

        self.assertNotIn("show:: [[Test Show]]", result)
        self.assertNotIn("host:: [[Test Host]]", result)
        self.assertNotIn("![Image]", result)
        self.assertIn("episode-link::", result)  # Should keep episode-specific metadata

    def test_fix_publish_date_format(self):
        """Test fixing publish date format."""
        content = "  publish-date:: [[2025-01-01]]"
        result = self.splitter._fix_publish_date_format(content)
        self.assertEqual(result, "  publish-date:: 2025-01-01")

    def test_clean_up_formatting(self):
        """Test cleaning up formatting."""
        content = "Line 1\n\n\n\nLine 2"
        result = self.splitter._clean_up_formatting(content)
        self.assertEqual(result, "Line 1\n\nLine 2")

    def test_remove_show_notes_section(self):
        """Test removing show notes section."""
        content = """- ### Summary
Content here

- ### Show notes
#+BEGIN_QUOTE
These should be removed
#+END_QUOTE

- ### More content"""

        result = self.splitter._remove_show_notes_section(content)

        self.assertIn("- ### Summary", result)
        self.assertIn("- ### More content", result)
        self.assertNotIn("Show notes", result)
        self.assertNotIn("These should be removed", result)

    def test_handle_collapsed_sections(self):
        """Test handling collapsed sections."""
        content = """collapsed:: true
- #### **📚 Transcript**
  collapsed:: true
  Some transcript content
collapsed:: true"""

        result = self.splitter._handle_collapsed_sections(content)

        # Should preserve transcript collapsed but remove others
        # The result should have transcript collapsed preserved, but standalone ones removed
        self.assertIn("**📚 Transcript**", result)
        self.assertIn("collapsed:: true", result)  # The transcript one should remain

        # Count occurrences - should be fewer after removal
        original_count = content.count("collapsed:: true")
        result_count = result.count("collapsed:: true")
        self.assertLess(result_count, original_count)

    def test_format_transcript_content(self):
        """Test transcript content formatting."""
        content = """- #### **📚 Transcript**
  #+BEGIN_QUOTE
  **Speaker 1**
  Regular content
  **Speaker 2**
  More content
  #+END_QUOTE"""

        result = self.splitter._format_transcript_content(content)
        lines = result.split('\n')

        # Check that content inside transcript is properly indented
        for line in lines:
            if 'Speaker' in line or 'Regular content' in line or 'More content' in line:
                self.assertTrue(line.startswith('    ') or line.startswith('      '))

    def test_get_existing_episode_titles_no_file(self):
        """Test getting existing titles when file doesn't exist."""
        non_existent_file = Path(self.temp_dir) / "non_existent.md"
        titles = self.splitter._get_existing_episode_titles(non_existent_file)
        self.assertEqual(len(titles), 0)

    def test_get_existing_episode_titles_with_file(self):
        """Test getting existing titles from file."""
        test_file = Path(self.temp_dir) / "existing.md"
        content = """- ## [[Episode 1]]
Some content
- ## Episode 2
More content"""

        test_file.write_text(content)
        titles = self.splitter._get_existing_episode_titles(test_file)

        self.assertEqual(len(titles), 2)
        self.assertIn("Episode 1", titles)
        self.assertIn("Episode 2", titles)

    def test_safe_file_write(self):
        """Test safe file writing."""
        test_file = Path(self.temp_dir) / "test_write.md"
        content = "Test content"

        result = safe_file_write(test_file, content)

        self.assertTrue(result)
        self.assertTrue(test_file.exists())
        self.assertEqual(test_file.read_text(), content)

    def test_safe_file_append(self):
        """Test safe file appending."""
        test_file = Path(self.temp_dir) / "test_append.md"
        initial_content = "Initial content"
        append_content = "\nAppended content"

        test_file.write_text(initial_content)
        result = safe_file_append(test_file, append_content)

        self.assertTrue(result)
        final_content = test_file.read_text()
        self.assertEqual(final_content, initial_content + append_content)

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        timestamp = format_current_timestamp()

        # Should be in format YYYY-MM-DD HH:MM:SS
        self.assertRegex(timestamp, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')

    def test_insert_new_episodes_after_properties_on_update(self):
        """Ensure new episodes are inserted right after the Logseq properties block."""
        show_name = "Test Show"
        filename = f"Podcasts___{sanitize_filename(show_name)}.md"
        show_file = Path(self.temp_dir) / filename

        # Existing file with properties at top and some old content
        existing_content = (
            "type:: podcast\n"
            f"show:: {show_name}\n"
            "episode-count:: 0\n"
            "last-episode-date:: 2025-01-01\n\n"
            "OLD_CONTENT\n"
        )
        show_file.write_text(existing_content)

        # New episode for the same show
        new_episode_content = (
            "- ## [[Brand New Episode]]\n"
            "  publish-date:: [[2025-01-10]]\n"
            f"  show:: [[{show_name}]]\n"
            "\n- ### Summary\n  New summary here.\n"
        )
        episode = SnipdEpisode(
            title="Brand New Episode",
            show=show_name,
            content=new_episode_content,
            publish_date="2025-01-10",
        )

        splitter = SnipdSplitter(str(self.test_input_file), self.temp_dir)
        shows = {show_name: [episode]}
        metadata = {show_name: ShowMetadata(show_name)}

        splitter.write_show_files(shows, metadata)

        updated = show_file.read_text()

        # The timestamp marker and new episode should come before OLD_CONTENT
        self.assertIn("<!-- New episodes added on ", updated)
        self.assertLess(
            updated.find("- ## Brand New Episode"),
            updated.find("OLD_CONTENT")
        )
        # Properties should remain at the very top
        self.assertTrue(updated.startswith("type:: podcast\n"))

        # Episode count should reflect addition (existing titles are zero in this minimal test)
        self.assertIn("episode-count:: 1", updated)
        # last-episode-date should be updated to the latest date
        self.assertIn("last-episode-date:: 2025-01-10", updated)

    def test_prepare_episode_content(self):
        """Test episode content preparation."""
        episode1 = SnipdEpisode("Episode 1", "Show", "Content 1")
        episode2 = SnipdEpisode("Episode 2", "Show", "Content 2\n")  # One with trailing newline

        episodes = [episode1, episode2]
        result = self.splitter._prepare_episode_content(episodes)

        self.assertIn("Content 1", result)
        self.assertIn("Content 2", result)
        self.assertTrue(result.endswith('\n'))

    def test_transform_episode_to_namespace_integration(self):
        """Test the complete episode transformation pipeline."""
        result = self.splitter._transform_episode_to_namespace(
            SnipdEpisode("Test Episode", "Test Show", self.sample_episode_text)
        )

        # Should have removed brackets from title
        self.assertNotIn("[[Test Episode Title]]", result)
        self.assertIn("Test Episode Title", result)

        # Should have removed show metadata
        self.assertNotIn("show:: [[Test Show]]", result)
        self.assertNotIn("host:: [[Test Host]]", result)

        # Should have fixed publish date format
        self.assertNotIn("[[2025-01-01]]", result)
        self.assertIn("publish-date:: 2025-01-01", result)

        # Should have removed show notes
        self.assertNotIn("Show notes", result)
        self.assertNotIn("These are show notes that should be removed", result)


class TestSnipdSplitterIntegration(unittest.TestCase):
    """Integration tests for the SnipdSplitter."""

    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_input_file = Path(self.temp_dir) / "test_input.md"

        # Create sample input file
        sample_content = """# Snipd Export

- ## [[Episode 1]]
  episode-link:: [Open in Snipd](https://example.com/ep1)
  publish-date:: [[2025-01-01]]
  show:: [[Test Show]]
  host:: [[Test Host]]
  ![Image](https://example.com/thumb1.jpg)

- ### Summary
  Episode 1 summary

- ## [[Episode 2]]
  episode-link:: [Open in Snipd](https://example.com/ep2)
  publish-date:: [[2025-01-02]]
  show:: [[Test Show]]
  host:: [[Test Host]]
  ![Image](https://example.com/thumb2.jpg)

- ### Summary
  Episode 2 summary

- ## [[Different Show Episode]]
  episode-link:: [Open in Snipd](https://example.com/ep3)
  publish-date:: [[2025-01-03]]
  show:: [[Different Show]]
  host:: [[Different Host]]

- ### Summary
  Different show episode summary
"""

        self.test_input_file.write_text(sample_content)
        self.splitter = SnipdSplitter(str(self.test_input_file), self.temp_dir)

    def tearDown(self):
        """Clean up integration test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_full_parsing_workflow(self):
        """Test the complete parsing workflow."""
        episodes = self.splitter.parse_episodes()

        self.assertEqual(len(episodes), 3)

        # Check first episode
        ep1 = episodes[0]
        self.assertEqual(ep1.title, "Episode 1")
        self.assertEqual(ep1.show, "Test Show")
        self.assertEqual(ep1.host, "Test Host")

        # Check third episode (different show)
        ep3 = episodes[2]
        self.assertEqual(ep3.title, "Different Show Episode")
        self.assertEqual(ep3.show, "Different Show")
        self.assertEqual(ep3.host, "Different Host")

    def test_grouping_by_show(self):
        """Test grouping episodes by show."""
        episodes = self.splitter.parse_episodes()
        shows, show_metadata = self.splitter.group_by_show(episodes)

        self.assertEqual(len(shows), 2)  # Two different shows
        self.assertIn("Test Show", shows)
        self.assertIn("Different Show", shows)

        # Test Show should have 2 episodes
        self.assertEqual(len(shows["Test Show"]), 2)
        self.assertEqual(len(shows["Different Show"]), 1)

        # Check metadata
        test_show_metadata = show_metadata["Test Show"]
        self.assertEqual(test_show_metadata.show_name, "Test Show")
        self.assertEqual(test_show_metadata.host, "Test Host")
        self.assertEqual(test_show_metadata.episode_count, 2)

    def test_complete_workflow(self):
        """Test the complete workflow end-to-end."""
        # Run the complete process
        episodes = self.splitter.parse_episodes()
        shows, show_metadata = self.splitter.group_by_show(episodes)
        self.splitter.write_show_files(shows, show_metadata)

        # Check that files were created
        expected_files = [
            "Podcasts___Test Show.md",
            "Podcasts___Different Show.md"
        ]

        for filename in expected_files:
            file_path = Path(self.temp_dir) / filename
            self.assertTrue(file_path.exists(), f"File {filename} should exist")

            # Check that files have content
            content = file_path.read_text()
            self.assertIn("type:: podcast", content)
            self.assertIn("episode-count::", content)

    def test_deduplication(self):
        """Test that duplicate episodes are not added."""
        # Run initial process
        episodes = self.splitter.parse_episodes()
        shows, show_metadata = self.splitter.group_by_show(episodes)
        self.splitter.write_show_files(shows, show_metadata)

        # Get initial file content
        test_show_file = Path(self.temp_dir) / "Podcasts___Test Show.md"
        initial_content = test_show_file.read_text()
        initial_length = len(initial_content)

        # Run again with same input - should not duplicate
        episodes2 = self.splitter.parse_episodes()
        shows2, show_metadata2 = self.splitter.group_by_show(episodes2)
        self.splitter.write_show_files(shows2, show_metadata2)

        # Check that file didn't grow (no new content added)
        final_content = test_show_file.read_text()
        final_length = len(final_content)

        # File should be same length or only slightly different (due to timestamp comments)
        self.assertAlmostEqual(final_length, initial_length, delta=100)

        # Should not contain duplicate episode headers
        episode_headers = final_content.count("- ## Episode 1") + final_content.count("- ## Episode 2")
        self.assertEqual(episode_headers, 2)  # One for each episode, no duplicates


if __name__ == '__main__':
    unittest.main(verbosity=2)
