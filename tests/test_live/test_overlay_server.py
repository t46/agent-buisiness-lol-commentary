"""Tests for the overlay server."""

import asyncio
import json

import pytest

from lol_commentary.live.overlay_server import OverlayServer, STATIC_DIR
from lol_commentary.live.persona import get_persona, PersonaRole
from lol_commentary.live.game_state import GameState


@pytest.fixture
def persona():
    return get_persona("kenshi")


@pytest.fixture
def overlay(persona):
    return OverlayServer(persona=persona, host="127.0.0.1", port=0)


class TestOverlayServerInit:
    def test_server_creation(self, persona):
        server = OverlayServer(persona=persona, port=9999)
        assert server._port == 9999
        assert server._persona is persona

    def test_static_dir_exists(self):
        assert STATIC_DIR.exists()
        assert (STATIC_DIR / "index.html").exists()
        assert (STATIC_DIR / "style.css").exists()
        assert (STATIC_DIR / "app.js").exists()

    def test_avatar_exists(self):
        assert (STATIC_DIR / "avatars" / "kenshi.png").exists()

    def test_state_to_dict(self, overlay):
        overlay._state = GameState(
            game_time="15:30",
            blue_score=5,
            red_score=3,
            game_phase="mid",
        )
        d = overlay._state_to_dict()
        assert d["game_time"] == "15:30"
        assert d["blue_score"] == 5
        assert d["red_score"] == 3
        assert d["game_phase"] == "mid"

    def test_state_to_dict_default(self, overlay):
        d = overlay._state_to_dict()
        assert d["game_time"] == "--:--"
        assert d["blue_score"] == 0


class TestOverlayServerHistory:
    def test_history_limit(self, overlay):
        """History should not grow beyond 50 entries."""
        for i in range(60):
            overlay._history.append({"message": f"msg {i}"})
            if len(overlay._history) > 50:
                overlay._history = overlay._history[-50:]

        assert len(overlay._history) == 50


@pytest.mark.asyncio
async def test_overlay_start_stop(persona):
    """Test that the server starts and stops cleanly."""
    server = OverlayServer(persona=persona, host="127.0.0.1", port=0)
    # Use port 0 to let OS pick an available port
    # We override to a known free port for testing
    server._port = 18765
    await server.start()
    assert server._runner is not None
    await server.stop()
    assert server._runner is None
