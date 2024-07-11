# podcast
Podcast download and post-processing (renaming, tagging).

## Usage
1) Provide url, artist and album of podcasts in a file named `serverlist` (see `serverlist_example`).
2) Update the podcast download directory in `podcast.py`
3) Run `python3 podcast.py`

## Dependencies
Python version: 3.10 or higher

Modules:
- `argparse`
- `calendar`
- `datetime`
- `inquirer`
- `json`
- `music_tag`
- `os`
- `pathlib`
- `re`
- `requests`
- `rss_parser`
- `unicodedata`
- `urllib.request`
