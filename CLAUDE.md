# LoL Commentary - AI実況解説システム

## Development

- Use `uv run` to execute Python commands
- Use `uv add` to add packages
- Use `uv run pytest` to run tests
- Python 3.13

## Project Structure

- `src/lol_commentary/` - Main source code
  - `video/` - Video download, frame extraction, OCR
  - `riot_api/` - Riot Games API integration
  - `knowledge/` - SQLite knowledge base
  - `analysis/` - Game analysis engine
  - `output/` - Commentary formatting and output
- `data/` - Runtime data (gitignored)
- `tests/` - Test suite

## Environment Variables

- `RIOT_API_KEY` - Riot Games API key (required)

## Slash Commands

- `/commentary <youtube-url>` - Analyze a LoL video and generate commentary
- `/update-knowledge` - Update knowledge base
- `/analyze-player <riot-id> <region>` - Analyze a player
