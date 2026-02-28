Analyze a League of Legends YouTube video and generate expert-level commentary.

## Steps

1. Run the analysis pipeline:
   ```
   uv run python -m lol_commentary analyze $ARGUMENTS
   ```

2. Read the generated output JSON file from `data/output/`

3. Review each commentary entry and enhance with deeper LoL analysis:
   - Add strategic context (why a play matters in the current game state)
   - Reference champion matchup knowledge
   - Explain macro implications of individual plays
   - Note power spike timings and item breakpoints

4. Present the final commentary in a chat-style format with timestamps, one message at a time.
