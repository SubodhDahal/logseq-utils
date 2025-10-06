# Logseq Utilities

A collection of Python scripts for managing and enhancing Logseq Knowledge Base workflows.

## Setup

Set the environment variable for your Logseq journal directory:
```
export LOGSEQ_JOURNAL_DIR="~/Documents/logseq/journals"
```

## Scripts

### Journal Cleaner (`clean_journal.py`)
Removes empty sections from journal entries to reduce clutter.

```
# Clean a specific date
python3 clean_journal.py --date 2024-01-15

# Clean all journals older than today
python3 clean_journal.py

# Clean all journals including today's
python3 clean_journal.py --all
```

It works with these journal file naming patterns:
- `YYYY-MM-DD.md` (default Logseq format)
- `YYYY_MM_DD.md` (underscore format)
- `journal_YYYY-MM-DD.md`
- `YYYY-MM-DD_journal.md`

### Snipd Logseq Export Splitter (`snipd-logseq-export-splitter/snipd_splitter.py`)

Splits large Snipd podcast exports into clean, show-specific Markdown files formatted for Logseq. It groups episodes by podcast, removes duplicate entries, and formats transcripts and metadata for seamless Logseq integration.

```
python3 snipd_splitter.py <input_file> [output_folder]
```

### Markdown to Logseq Outline (`md_to_logseq_outline.py`)
Converts longform Markdown into a Logseq-style outline, turning headings and paragraphs into nested bullets.

```
# From a file (default: per-line bullets)
python3 md_to_logseq_outline.py input.md > outline.md

# From stdin
cat input.md | python3 md_to_logseq_outline.py > outline.md

# Group consecutive lines into one bullet per paragraph block
python3 md_to_logseq_outline.py --paragraph-mode blocks input.md
```

Notes:
- ATX headings (e.g., `## Title`) become bullets like `- ## Title`.
- Non-empty lines become bullets under the latest heading; without a heading, they’re top-level.
- Setext headings (`===`/`---`) are minimally supported.
