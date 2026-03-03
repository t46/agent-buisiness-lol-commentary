"""Overlay server for OBS browser source via aiohttp + WebSocket."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from weakref import WeakSet

from aiohttp import web

from .game_state import GameState
from .persona import Persona

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "overlay" / "static"


class OverlayServer:
    """aiohttp server that serves the overlay page and pushes commentary via WebSocket."""

    def __init__(
        self,
        persona: Persona,
        host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:
        self._persona = persona
        self._host = host
        self._port = port
        self._app = web.Application()
        self._ws_clients: WeakSet[web.WebSocketResponse] = WeakSet()
        self._state = GameState()
        self._history: list[dict] = []
        self._runner: web.AppRunner | None = None

        self._app.router.add_get("/ws", self._ws_handler)
        self._app.router.add_static("/static", STATIC_DIR, show_index=False)
        self._app.router.add_get("/", self._index_handler)

    async def start(self) -> None:
        """Start the HTTP server."""
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()
        logger.info("Overlay server started at http://%s:%d", self._host, self._port)

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    async def _index_handler(self, request: web.Request) -> web.Response:
        """Serve the overlay HTML page."""
        index_path = STATIC_DIR / "index.html"
        return web.FileResponse(index_path)

    async def _ws_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._ws_clients.add(ws)
        logger.info("WebSocket client connected (total: %d)", len(self._ws_clients))

        # Send init message
        init_msg = {
            "type": "init",
            "persona": {
                "name": self._persona.name,
                "avatar": f"/static/avatars/{self._persona.avatar}",
                "role": self._persona.role.value,
            },
            "state": self._state_to_dict(),
            "history": self._history[-10:],
        }
        await ws.send_json(init_msg)

        try:
            async for msg in ws:
                pass  # Client doesn't send messages; just keep alive
        finally:
            self._ws_clients.discard(ws)
            logger.info("WebSocket client disconnected (total: %d)", len(self._ws_clients))

        return ws

    async def update_state(self, state: GameState) -> None:
        """Push a state update to all connected clients."""
        self._state = state
        msg = {
            "type": "state",
            "data": self._state_to_dict(),
        }
        await self._broadcast(msg)

    async def add_commentary(
        self,
        message: str,
        significance: float,
        persona_name: str | None = None,
    ) -> None:
        """Push a commentary message to all connected clients."""
        excitement = self._persona.get_excitement(significance)
        data = {
            "message": message,
            "significance": significance,
            "excitement": excitement,
            "persona_name": persona_name or self._persona.name,
        }
        self._history.append(data)
        if len(self._history) > 50:
            self._history = self._history[-50:]

        msg = {"type": "commentary", "data": data}
        await self._broadcast(msg)

    async def _broadcast(self, msg: dict) -> None:
        """Send a message to all connected WebSocket clients."""
        dead: list[web.WebSocketResponse] = []
        for ws in self._ws_clients:
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._ws_clients.discard(ws)

    def _state_to_dict(self) -> dict:
        return {
            "game_time": self._state.game_time or "--:--",
            "blue_score": self._state.blue_score,
            "red_score": self._state.red_score,
            "game_phase": self._state.game_phase,
        }
