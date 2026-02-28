-- LoL Commentary Knowledge Base Schema

CREATE TABLE IF NOT EXISTS champions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    title TEXT DEFAULT '',
    roles TEXT DEFAULT '',  -- comma-separated: Fighter,Tank
    resource_type TEXT DEFAULT 'MANA',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS champion_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    champion_id INTEGER NOT NULL,
    patch TEXT NOT NULL,
    role TEXT NOT NULL,  -- TOP, JUNGLE, MID, BOT, SUPPORT
    win_rate REAL DEFAULT 0.0,
    pick_rate REAL DEFAULT 0.0,
    ban_rate REAL DEFAULT 0.0,
    avg_kda REAL DEFAULT 0.0,
    popular_build TEXT DEFAULT '',  -- JSON array of item IDs
    popular_runes TEXT DEFAULT '',  -- JSON
    sample_size INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(champion_id, patch, role),
    FOREIGN KEY (champion_id) REFERENCES champions(id)
);

CREATE TABLE IF NOT EXISTS champion_matchups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    champion_id INTEGER NOT NULL,
    opponent_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    win_rate REAL DEFAULT 0.5,
    gold_diff_15 REAL DEFAULT 0.0,
    sample_size INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(champion_id, opponent_id, role),
    FOREIGN KEY (champion_id) REFERENCES champions(id),
    FOREIGN KEY (opponent_id) REFERENCES champions(id)
);

CREATE TABLE IF NOT EXISTS players (
    puuid TEXT PRIMARY KEY,
    riot_id TEXT NOT NULL,
    tag_line TEXT DEFAULT '',
    region TEXT DEFAULT 'jp1',
    rank TEXT DEFAULT '',
    tier TEXT DEFAULT '',
    lp INTEGER DEFAULT 0,
    main_role TEXT DEFAULT '',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS player_champion_pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    puuid TEXT NOT NULL,
    champion_id INTEGER NOT NULL,
    games_played INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0.0,
    avg_kda REAL DEFAULT 0.0,
    last_played TIMESTAMP,
    UNIQUE(puuid, champion_id),
    FOREIGN KEY (puuid) REFERENCES players(puuid),
    FOREIGN KEY (champion_id) REFERENCES champions(id)
);

CREATE TABLE IF NOT EXISTS meta_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patch TEXT NOT NULL,
    tier TEXT DEFAULT 'all',  -- all, challenger, master, diamond, etc.
    role TEXT DEFAULT 'all',
    top_champions TEXT DEFAULT '',  -- JSON array
    banned_champions TEXT DEFAULT '',  -- JSON array
    meta_notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(patch, tier, role)
);

CREATE TABLE IF NOT EXISTS analyzed_games (
    match_id TEXT PRIMARY KEY,
    patch TEXT DEFAULT '',
    duration INTEGER DEFAULT 0,
    winner TEXT DEFAULT '',  -- blue or red
    blue_team_comp TEXT DEFAULT '',  -- JSON
    red_team_comp TEXT DEFAULT '',  -- JSON
    analysis_json TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS play_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type TEXT NOT NULL,  -- gank, teamfight, objective, trade, rotation
    description TEXT DEFAULT '',
    rating TEXT DEFAULT 'neutral',  -- excellent, good, neutral, questionable, poor
    context_json TEXT DEFAULT '',
    frequency INTEGER DEFAULT 1,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_champion_stats_patch ON champion_stats(patch);
CREATE INDEX IF NOT EXISTS idx_champion_stats_champion ON champion_stats(champion_id);
CREATE INDEX IF NOT EXISTS idx_matchups_champion ON champion_matchups(champion_id);
CREATE INDEX IF NOT EXISTS idx_player_pool_puuid ON player_champion_pool(puuid);
CREATE INDEX IF NOT EXISTS idx_meta_patch ON meta_snapshots(patch);
