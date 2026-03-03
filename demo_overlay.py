"""Demo script: overlay server + simulated game events with pre-written commentary.

Usage:
    uv run python demo_overlay.py

Then open http://127.0.0.1:8765 in a browser (or add as OBS browser source).
"""

import asyncio
import random

from lol_commentary.live.overlay_server import OverlayServer
from lol_commentary.live.game_state import GameState
from lol_commentary.live.persona import get_persona


# Pre-written commentary simulating a LoL match
GAME_SCRIPT = [
    # (delay_sec, game_time, blue_score, red_score, phase, commentary, significance)
    (3, "01:30", 0, 0, "early", None, 0),
    (5, "03:15", 1, 0, "early",
     "ファーストブラッド！ブルー側のジャングラーがトップレーンにガンク、見事にキルを獲得！序盤のプレッシャーはブルー側が一歩リードです。",
     0.6),
    (12, "05:42", 1, 1, "early",
     "レッド側がボットレーンで反撃！サポートのフックが綺麗に刺さりました。これでスコアはイーブン、まだまだ序盤の駆け引きが続きます。",
     0.5),
    (8, "07:20", 2, 1, "early",
     "ミッドレーンでソロキル！ブルー側のミッドレーナーがレベル6のパワースパイクを活かしました。この判断は見事ですね。",
     0.55),
    (30, "10:00", 2, 1, "early",
     "さて、10分が経過しました。ブルー側が1キルリードしていますが、CS差を見るとレッド側も悪くない。次のドラゴンが鍵になりそうですね。",
     0.2),  # fill comment
    (10, "12:45", 3, 2, "mid",
     "中盤に入りました！ドラゴン周りで小規模な戦闘が発生、両チームともに1キルずつ交換。ブルー側がドラゴンを確保！これは大きいですよ。",
     0.7),
    (8, "14:30", 4, 2, "mid",
     "来ました！ブルー側のジャングラーが再びガンク！ボットレーンのタワーダイブが成功、レッド側のADCを倒しました。",
     0.6),
    (15, "16:00", 4, 4, "mid",
     "うおおおお！集団戦発生！レッド側が見事なエンゲージで2キルを獲得！一気にスコアが並びました！これはゲームの流れが変わるかもしれません！",
     0.85),
    (30, "19:30", 4, 4, "mid",
     "両チームともに慎重な動きですね。次のバロンタイマーを意識しているのでしょう。ここからのマクロの判断が勝敗を分けそうです。",
     0.2),  # fill
    (10, "21:15", 5, 5, "mid",
     "互いにキルを交換！スコアは5-5の完全なイーブン。手に汗握る展開です。",
     0.5),
    (8, "23:00", 5, 5, "mid",
     "バロンの視界を巡る攻防が始まりました。さあどうする、ここからの判断が全てを決める…！",
     0.4),
    (10, "25:30", 7, 5, "late",
     "信じられない！！バロンファイト中にブルー側がスティール成功！さらにそのまま2キルを獲得！！これは完全にゲームチェンジャーです！！！",
     0.95),
    (15, "28:00", 8, 6, "late",
     "バロンバフを活かしてブルー側がインヒビターを破壊！レッド側は必死のディフェンスですが、ゴールド差がじわじわと広がっています。",
     0.7),
    (10, "30:45", 10, 6, "late",
     "最後の集団戦！ブルー側のADCが神がかったポジショニングでトリプルキル！！GG！ブルー側の勝利です！素晴らしい試合でした！",
     0.95),
]


async def main():
    persona = get_persona("kenshi")
    server = OverlayServer(persona=persona, host="127.0.0.1", port=8765)
    await server.start()

    print("=" * 60)
    print("  LoL AI Commentary Overlay Demo")
    print("=" * 60)
    print()
    print("  Open in browser:  http://127.0.0.1:8765")
    print("  (or add as OBS Browser Source)")
    print()
    print("  Simulating a full match...")
    print("  Press Ctrl+C to stop")
    print()
    print("-" * 60)

    try:
        # Initial wait for client connection
        await asyncio.sleep(2)

        for delay, game_time, blue, red, phase, commentary, significance in GAME_SCRIPT:
            # Update game state
            state = GameState(
                game_time=game_time,
                game_time_seconds=int(game_time.split(":")[0]) * 60 + int(game_time.split(":")[1]),
                blue_score=blue,
                red_score=red,
                game_phase=phase,
            )
            await server.update_state(state)
            print(f"  [{game_time}] Score: Blue {blue} - {red} Red ({phase})")

            if commentary:
                await asyncio.sleep(1)  # Brief pause before commentary
                await server.add_commentary(commentary, significance)
                excitement = persona.get_excitement(significance)
                print(f"           [{excitement}] {commentary[:60]}...")

            await asyncio.sleep(delay)

        print()
        print("  Match complete! Overlay will stay running.")
        print("  Press Ctrl+C to stop.")
        print()

        # Keep server running
        while True:
            await asyncio.sleep(1)

    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await server.stop()
        print("\n  Server stopped.")


if __name__ == "__main__":
    asyncio.run(main())
