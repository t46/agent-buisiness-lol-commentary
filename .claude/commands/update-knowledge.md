Update the LoL knowledge base with the latest champion, item, and meta data.

Run the update command:
```
uv run python -m lol_commentary update-knowledge $ARGUMENTS
```

This will:
- Fetch the latest Data Dragon version
- Update champion data (names, roles, abilities)
- Update item data (stats, build paths, costs)
- Store everything in the local knowledge base (data/knowledge.db)
