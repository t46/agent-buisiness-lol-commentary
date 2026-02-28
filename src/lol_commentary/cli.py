from __future__ import annotations
import json
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import get_settings

console = Console()
logger = logging.getLogger("lol_commentary")


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool):
    """LoL AI Commentary System - AI実況解説システム"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@cli.command()
@click.argument("url")
@click.option("--output", "-o", type=click.Path(), help="Output JSON file path")
@click.option("--match-id", type=str, help="Manually specify match ID (skip auto-detection)")
@click.option("--no-download", is_flag=True, help="Skip video download (metadata only)")
def analyze(url: str, output: str | None, match_id: str | None, no_download: bool):
    """Analyze a LoL YouTube video and generate commentary.

    Usage: lol-commentary analyze <youtube-url>
    """
    settings = get_settings()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Step 1: Extract video info
        task = progress.add_task("動画情報を取得中...", total=None)
        try:
            from .video.downloader import VideoDownloader
            downloader = VideoDownloader(settings.DATA_DIR / "videos")
            video_info = downloader.extract_info(url)
            console.print(f"[green]✓[/green] 動画: {video_info.title}")
            console.print(f"  長さ: {video_info.duration // 60}:{video_info.duration % 60:02d}")
            progress.update(task, description="動画情報取得完了")
        except Exception as e:
            console.print(f"[red]✗ 動画情報の取得に失敗: {e}[/red]")
            sys.exit(1)

        # Step 2: Download video (if needed)
        if not no_download:
            progress.update(task, description="動画をダウンロード中...")
            try:
                video_info = downloader.download(url)
                console.print(f"[green]✓[/green] ダウンロード完了: {video_info.filepath}")
            except Exception as e:
                console.print(f"[yellow]⚠ ダウンロード失敗 (メタデータのみで続行): {e}[/yellow]")

        # Step 3: Fetch transcript
        progress.update(task, description="字幕を取得中...")
        try:
            from .video.transcript import TranscriptFetcher
            fetcher = TranscriptFetcher()
            transcript = fetcher.fetch(video_info.video_id)
            if transcript:
                console.print(f"[green]✓[/green] 字幕取得: {len(transcript)}セグメント")
            else:
                console.print("[yellow]⚠ 字幕なし[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠ 字幕取得失敗: {e}[/yellow]")
            transcript = []

        # Step 4: OCR (if video downloaded)
        player_names = []
        if video_info.filepath and video_info.filepath.exists():
            progress.update(task, description="OCRでプレイヤー名を抽出中...")
            try:
                from .video.frame_extractor import FrameExtractor
                from .video.ocr_engine import OCREngine

                with FrameExtractor(video_info.filepath) as extractor:
                    # Extract a frame from early game (around 2 minutes)
                    frame = extractor.extract_at_time(120)
                    if frame:
                        hud = extractor.get_hud_regions(frame.frame)
                        ocr = OCREngine()
                        names = ocr.extract_all_player_names(
                            hud.get("blue_player_names", []),
                            hud.get("red_player_names", []),
                        )
                        player_names = names.get("blue", []) + names.get("red", [])
                        if player_names:
                            console.print(f"[green]✓[/green] プレイヤー名検出: {', '.join(player_names)}")
            except Exception as e:
                console.print(f"[yellow]⚠ OCR失敗: {e}[/yellow]")

        # Also try parsing names from title
        title_names = VideoDownloader.parse_player_names_from_title(video_info.title)
        player_names.extend(n for n in title_names if n not in player_names)

        # Step 5: Find match via Riot API
        found_match_id = match_id
        if not found_match_id and player_names:
            progress.update(task, description="マッチを検索中...")
            try:
                from .riot_api.client import RiotAPIClient
                from .riot_api.match_finder import MatchFinder
                from datetime import datetime

                client = RiotAPIClient(
                    api_key=settings.RIOT_API_KEY,
                    region=settings.REGION,
                    cache_dir=settings.CACHE_DIR,
                )
                finder = MatchFinder(client)
                upload_date = datetime.strptime(video_info.upload_date, "%Y%m%d") if video_info.upload_date else datetime.now()
                found_match_id = finder.find_match(player_names, upload_date)
                if found_match_id:
                    console.print(f"[green]✓[/green] マッチ特定: {found_match_id}")
                else:
                    console.print("[yellow]⚠ マッチが見つかりませんでした[/yellow]")
            except Exception as e:
                console.print(f"[yellow]⚠ マッチ検索失敗: {e}[/yellow]")

        if not found_match_id:
            console.print("[red]マッチIDが特定できませんでした。--match-id オプションで指定してください。[/red]")
            sys.exit(1)

        # Step 6: Fetch and parse timeline
        progress.update(task, description="タイムラインを解析中...")
        try:
            from .riot_api.client import RiotAPIClient
            from .riot_api.timeline_parser import TimelineParser

            if 'client' not in locals():
                client = RiotAPIClient(
                    api_key=settings.RIOT_API_KEY,
                    region=settings.REGION,
                    cache_dir=settings.CACHE_DIR,
                )

            match_info = client.get_match(found_match_id)
            raw_timeline = client.get_match_timeline(found_match_id)
            parser = TimelineParser()
            events = parser.parse(raw_timeline)
            console.print(f"[green]✓[/green] タイムライン: {len(events)}イベント")
        except Exception as e:
            console.print(f"[red]✗ タイムライン取得失敗: {e}[/red]")
            sys.exit(1)

        # Step 7: Analysis
        progress.update(task, description="ゲーム分析中...")
        try:
            from .analysis.segmenter import GameSegmenter
            from .analysis.event_classifier import EventClassifier
            from .analysis.play_evaluator import PlayEvaluator
            from .analysis.draft_analyzer import DraftAnalyzer
            from .analysis.team_analyzer import TeamAnalyzer
            from .output.segment_context import (
                CommentaryEntry, CommentaryOutput, GameContext,
            )

            # Segment the game
            segmenter = GameSegmenter()
            segments = segmenter.segment(events, match_info.game_duration * 1000)

            # Classify events
            classifier = EventClassifier()

            # Draft analysis
            draft_analyzer = DraftAnalyzer()
            draft = draft_analyzer.analyze(match_info)

            # Team analysis
            team_analyzer = TeamAnalyzer()
            team_analyses = team_analyzer.analyze(match_info, events)

            # Play evaluation
            evaluator = PlayEvaluator()

            # Build commentary
            blue_players = [p for p in match_info.participants if p.team_id == 100]
            red_players = [p for p in match_info.participants if p.team_id == 200]
            winner = "blue" if any(p.win for p in blue_players) else "red"

            duration_secs = match_info.game_duration
            game_ctx = GameContext(
                match_id=found_match_id,
                patch=match_info.game_version.rsplit(".", 1)[0] if "." in match_info.game_version else match_info.game_version,
                duration=f"{duration_secs // 60}:{duration_secs % 60:02d}",
                blue_team=[p.riot_id_game_name or p.champion_name for p in blue_players],
                red_team=[p.riot_id_game_name or p.champion_name for p in red_players],
                blue_champions=[p.champion_name for p in blue_players],
                red_champions=[p.champion_name for p in red_players],
                draft_analysis=draft.matchup_summary,
                winner=winner,
            )

            commentary_entries = []

            # Add draft commentary at start
            commentary_entries.append(CommentaryEntry(
                video_time="00:00",
                game_time="00:00",
                type="overall",
                message=draft.matchup_summary,
                significance=0.7,
            ))

            # Process each segment
            for segment in segments:
                for event in segment.events:
                    score = classifier.classify(event)
                    if score.total < 0.2:
                        continue

                    game_secs = event.timestamp // 1000
                    game_time = f"{game_secs // 60:02d}:{game_secs % 60:02d}"
                    # Approximate video time (could be offset)
                    video_time = game_time

                    # Determine commentary type
                    if event.type == "CHAMPION_KILL":
                        evaluation = evaluator.evaluate_kill(event, match_info)
                        entry_type = "player"
                        message = f"{evaluation.reason}。{evaluation.impact}"
                    elif event.type in ("ELITE_MONSTER_KILL", "BUILDING_KILL"):
                        evaluation = evaluator.evaluate_objective(event, match_info)
                        entry_type = "team"
                        message = f"【{score.reason}】{evaluation.reason}"
                    else:
                        entry_type = "overall"
                        message = score.reason

                    commentary_entries.append(CommentaryEntry(
                        video_time=video_time,
                        game_time=game_time,
                        type=entry_type,
                        message=message,
                        significance=score.total,
                    ))

                # Add macro commentary for macro segments
                if segment.segment_type == "macro" and not segment.events:
                    game_secs = segment.start_time // 1000
                    game_time = f"{game_secs // 60:02d}:{game_secs % 60:02d}"

                    # Generate macro observation
                    blue_macro = team_analyses["blue"]
                    red_macro = team_analyses["red"]
                    obs = []
                    for team_analysis in [blue_macro, red_macro]:
                        obs.extend(team_analysis.key_observations[:1])

                    if obs:
                        commentary_entries.append(CommentaryEntry(
                            video_time=game_time,
                            game_time=game_time,
                            type="team",
                            message=f"マクロ状況: {'. '.join(obs)}",
                            significance=0.3,
                        ))

            # Sort by game time
            commentary_entries.sort(key=lambda e: e.game_time)

            commentary_output = CommentaryOutput(
                game_info=game_ctx,
                commentary=commentary_entries,
            )
            console.print(f"[green]✓[/green] 解説生成: {len(commentary_entries)}エントリ")
        except Exception as e:
            console.print(f"[red]✗ 分析失敗: {e}[/red]")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        # Step 8: Output
        progress.update(task, description="出力中...")
        from .output.formatter import CommentaryFormatter
        formatter = CommentaryFormatter(console)

        if output:
            output_path = Path(output)
            json_str = formatter.to_json(commentary_output, output_path)
            console.print(f"[green]✓[/green] JSON出力: {output_path}")
        else:
            # Default: output to data/output/<match_id>.json
            output_path = settings.DATA_DIR / "output" / f"{found_match_id}.json"
            json_str = formatter.to_json(commentary_output, output_path)
            console.print(f"[green]✓[/green] JSON出力: {output_path}")

        # Display rich output
        formatter.display_rich(commentary_output)
        formatter.display_summary(commentary_output)

    console.print("[bold green]完了![/bold green]")


@cli.command("update-knowledge")
@click.option("--patch", type=str, help="Specific patch version to update")
def update_knowledge(patch: str | None):
    """Update knowledge base from Data Dragon."""
    settings = get_settings()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("知識ベースを更新中...", total=None)

        try:
            from .knowledge.database import Database
            from .knowledge.champion_kb import ChampionKB
            from .riot_api.data_dragon import DataDragonClient

            db = Database(settings.DATA_DIR / "knowledge.db")
            champion_kb = ChampionKB(db)
            dd = DataDragonClient(settings.CACHE_DIR / "ddragon")

            version = patch or dd.get_latest_version()
            console.print(f"パッチ {version} のデータを取得中...")

            champions = dd.get_champions(version)
            champion_kb.bulk_update_from_data_dragon(champions)
            console.print(f"[green]✓[/green] {len(champions)} チャンピオンを更新")

            items = dd.get_items(version)
            console.print(f"[green]✓[/green] {len(items)} アイテムを更新")

            progress.update(task, description="更新完了")
        except Exception as e:
            console.print(f"[red]✗ 更新失敗: {e}[/red]")
            sys.exit(1)

    console.print("[bold green]知識ベース更新完了![/bold green]")


@cli.command("analyze-player")
@click.argument("riot_id")
@click.option("--region", "-r", default="jp1", help="Region (default: jp1)")
@click.option("--tag", "-t", default="JP1", help="Tag line (default: JP1)")
def analyze_player(riot_id: str, region: str, tag: str):
    """Look up and analyze a player's stats."""
    settings = get_settings()

    try:
        from .riot_api.client import RiotAPIClient
        from .knowledge.database import Database
        from .knowledge.player_kb import PlayerKB

        client = RiotAPIClient(
            api_key=settings.RIOT_API_KEY,
            region=region,
            cache_dir=settings.CACHE_DIR,
        )

        console.print(f"プレイヤー検索: {riot_id}#{tag}")
        account = client.get_account_by_riot_id(riot_id, tag)
        puuid = account["puuid"]
        console.print(f"[green]✓[/green] PUUID: {puuid[:8]}...")

        # Check knowledge base
        db = Database(settings.DATA_DIR / "knowledge.db")
        player_kb = PlayerKB(db)
        player = player_kb.get_player(puuid)

        if player:
            console.print(f"\n[bold]プレイヤー情報:[/bold]")
            console.print(f"  Riot ID: {player['riot_id']}#{player['tag_line']}")
            console.print(f"  ランク: {player.get('tier', 'N/A')} {player.get('rank', '')}")

            pool = player_kb.get_champion_pool(puuid)
            if pool:
                console.print(f"\n[bold]チャンピオンプール:[/bold]")
                for champ in pool[:10]:
                    console.print(
                        f"  {champ.get('champion_name', 'Unknown')}: "
                        f"{champ['games_played']}試合, "
                        f"勝率{champ['win_rate']*100:.0f}%, "
                        f"KDA {champ['avg_kda']:.1f}"
                    )
        else:
            console.print("[yellow]知識ベースにデータなし。マッチ解析後に蓄積されます。[/yellow]")

        # Fetch recent matches
        console.print(f"\n[bold]最近のマッチ:[/bold]")
        matches = client.get_match_list(puuid, count=5)
        for mid in matches:
            try:
                match_data = client.get_match(mid)
                p = next((p for p in match_data.participants if p.puuid == puuid), None)
                if p:
                    result = "[green]WIN[/green]" if p.win else "[red]LOSS[/red]"
                    console.print(
                        f"  {mid}: {p.champion_name} "
                        f"{p.kills}/{p.deaths}/{p.assists} "
                        f"{result}"
                    )
            except Exception:
                console.print(f"  {mid}: データ取得失敗")

    except Exception as e:
        console.print(f"[red]✗ プレイヤー分析失敗: {e}[/red]")
        sys.exit(1)


def main():
    cli()
