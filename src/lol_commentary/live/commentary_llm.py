from __future__ import annotations

import logging
import time

import anthropic

from .event_detector import LiveEvent
from .game_state import GameState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
あなたはLeague of Legendsの元プロ選手で、現在はトップレベルの実況解説者です。
視聴者がプレイヤーの頭の中を覗けるような、深い解説をしてください。

## 解説スタイル

1. **何が起きたか** — 事実を簡潔に
2. **なぜそうなったか** — プレイヤーの判断・意図を読み解く
   - 「おそらくこのキルは○○を狙ったローテーションの結果ですね」
   - 「この動きは次のドラゴンを見据えた布石でしょう」
3. **何がすごいのか / 何がまずいのか** — プレイの質を評価
   - ナイスプレイなら「この判断は見事」「タイミングが完璧」
   - ミスなら「ここは少し前に出すぎましたね」
4. **次に何が起きそうか** — 展開を予測
   - 「このキル差ならドラゴン争奪戦で有利に立てるはず」
   - 「ゴールド差が開いてきたので、レッド側はスプリットプッシュに切り替えたいところ」

## トーンとフォーマット

- 熱量のある実況口調（「来ました！」「これは大きい！」「さあどうする！」）
- ただし冷静な分析も混ぜる（実況と解説のバランス）
- 3-5文程度で、テンポよく
- ゲームフェーズに応じた視点を持つ:
  - 序盤: レーン戦の駆け引き、ジャングルの影響力、ファーストブラッドの意味
  - 中盤: オブジェクト争奪、ローテーション、パワースパイク
  - 終盤: 集団戦のポジショニング、バロン/エルダー争い、一発逆転の可能性
"""


class CommentaryLLM:
    """Generate natural commentary text using Claude API."""

    MODEL = "claude-haiku-4-5-20251001"
    def __init__(self, api_key: str, **_kwargs) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._history: list[LiveEvent] = []

    async def generate(
        self, event: LiveEvent, state: GameState, history: list[LiveEvent]
    ) -> str | None:
        """Generate commentary for an event."""
        self._history.append(event)

        # Build context
        phase_name = {"early": "序盤", "mid": "中盤", "late": "終盤"}.get(state.game_phase, state.game_phase)

        # Kill differential and momentum
        kill_diff = state.blue_score - state.red_score
        if kill_diff > 0:
            momentum = f"ブルー側が{kill_diff}キルリード"
        elif kill_diff < 0:
            momentum = f"レッド側が{abs(kill_diff)}キルリード"
        else:
            momentum = "キルスコアは互角"

        context = (
            f"## 現在の状況\n"
            f"- ゲーム時間: {state.game_time or '不明'}\n"
            f"- スコア: ブルー {state.blue_score} - {state.red_score} レッド ({momentum})\n"
            f"- フェーズ: {phase_name}\n"
        )

        # Recent events context (for narrative flow)
        recent = self._history[-8:]
        if len(recent) > 1:
            context += "\n## 直近の流れ\n"
            for e in recent[:-1]:
                context += f"- [{e.game_time}] {e.description}\n"

        user_message = (
            f"{context}\n"
            f"## 今発生したイベント\n"
            f"{event.description}\n"
            f"重要度: {event.significance:.1f}\n\n"
            f"このイベントについて、プレイヤーの意図や判断を読み解きながら解説してください。"
        )

        try:
            response = await self._client.messages.create(
                model=self.MODEL,
                max_tokens=800,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error("Commentary generation failed: %s", e)
            return None
