# Snipd Logseq Export Splitter

A Python script to break up big Snipd podcast exports into show-specific Markdown files for Logseq.

## Features

- Pulls out episodes with details like title, show, host, date, links
- Groups episodes by show; each show gets its own file
- Uses Logseq’s namespace format (`Podcasts___Show Name.md`)
- Skips episodes if they’re already present
- Cleans up content: removes extra metadata, formats transcripts, fixes episode titles, drops show notes
- Adds new episodes to existing files

## Requirements

- Python 3.6 or newer
- No extra packages (just Python’s built-in modules)

## How to Use

```
python3 snipd_splitter.py <input_file> [output_folder]
```

Example commands:

```
python3 snipd_splitter.py snipd_export.md
python3 snipd_splitter.py snipd_export.md ~/Documents/Podcasts
```

## Results

- One Markdown file per podcast show (`Podcasts___Show Name.md`)
- Each file has Logseq headers with episode count and dates
- Episodes are sorted by date

Sample file structure:

```
type:: podcast
show:: Show Name
host:: Host Name
episode-count:: 5
last-episode-date:: 2025-01-15

- ## Episode Title
  episode-link:: [Open in Snipd](https://example.com)
  publish-date:: 2025-01-15

  - ### Summary
    Quick overview...

  - #### **📚 Transcript**
    collapsed:: true
    - Transcript here...
```

## How It Works

1. Reads podcast episodes from the export
2. Groups them by show
3. Cleans and reformats
4. Writes or updates show files
5. Avoids adding duplicates

## Testing

Run tests with:

```
python3 test_snipd_splitter.py
```
