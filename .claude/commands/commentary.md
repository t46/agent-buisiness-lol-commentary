Analyze a League of Legends YouTube video and generate expert-level commentary.

## Steps

1. Run the analysis pipeline:
   ```
   uv run python -m lol_commentary analyze $ARGUMENTS
   ```

2. Check the output and determine the analysis mode:

### Level 1: Riot API成功 (analysis_mode = "riot_api")

If the pipeline succeeds with Riot API data:

1. Read the generated output JSON file from `data/output/`
2. Review each commentary entry and enhance with deeper LoL analysis:
   - Add strategic context (why a play matters in the current game state)
   - Reference champion matchup knowledge
   - Explain macro implications of individual plays
   - Note power spike timings and item breakpoints
3. Present the final commentary in a chat-style format with timestamps, one message at a time.

### Level 2: フレームベース出力あり (analysis_mode = "frame_based")

If the pipeline outputs frame-based analysis (Riot API was unavailable):

1. Read the generated output JSON file from `data/output/`
2. Read each frame image from the `frames` array using the Read tool to visually analyze the game state
3. Combine frame analysis with:
   - Video title information for context
   - Knowledge base (`data/knowledge.db`) for champion/item data
   - Transcript segments if available
4. Generate commentary based on what you observe in the frames:
   - Score changes and kill events
   - Objective takes (dragon, baron, tower)
   - Team compositions visible in the HUD
   - Item builds and power spikes
   - Map state and positioning
5. Present the commentary in a chat-style format with timestamps.

### Level 3: パイプライン失敗 → 直接分析

If the pipeline itself fails with an error:

1. Check if the video exists in `data/videos/`. If not, download it:
   ```
   uv run python -c "
   from lol_commentary.video.downloader import VideoDownloader
   from pathlib import Path
   d = VideoDownloader(Path('data/videos'))
   info = d.download('VIDEO_URL_HERE')
   print(f'Downloaded: {info.filepath}')
   "
   ```

2. Extract frames from the video:
   ```
   uv run python -c "
   from lol_commentary.video.frame_extractor import FrameExtractor
   from pathlib import Path
   import cv2
   video_path = Path('data/videos/VIDEO_FILE')
   frames_dir = Path('data/frames/VIDEO_ID')
   frames_dir.mkdir(parents=True, exist_ok=True)
   with FrameExtractor(video_path) as ext:
       frames = ext.extract_at_intervals(30.0, 60.0, min(ext.duration, 600.0))
       for i, f in enumerate(frames):
           cv2.imwrite(str(frames_dir / f'frame_{i:04d}_{f.timestamp:.0f}s.jpg'), f.frame)
       print(f'Extracted {len(frames)} frames to {frames_dir}')
   "
   ```

3. Read the extracted frame images using the Read tool to visually analyze each one
4. Query the knowledge base for champion and item information:
   ```
   uv run python -c "
   from lol_commentary.knowledge.database import Database
   from lol_commentary.knowledge.champion_kb import ChampionKB
   db = Database('data/knowledge.db')
   kb = ChampionKB(db)
   # Look up champions you identified in the frames
   "
   ```

5. Generate commentary directly based on your visual analysis of the frames, combining:
   - What you see in each frame (champions, items, map state, scores)
   - Knowledge base data about champions and items
   - Your understanding of LoL strategy and meta

6. Present the commentary in a chat-style format with timestamps.
