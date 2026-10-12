"""FastAPI endpoints for the shared pipeline."""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..config import Settings
from ..pipeline import PipelineRunner, build_default_runner

logger = logging.getLogger(__name__)


async def _send_stream(socket: WebSocket, runner: PipelineRunner) -> None:
    packet_version = report_version = 0
    while True:
        packet = await asyncio.to_thread(runner.wait_packet, packet_version, 0.5)
        if packet is not None:
            packet_version, data = packet
            await socket.send_bytes(data)
        report = runner.latest_report()
        if report is not None and report[0] != report_version:
            report_version, data = report
            await socket.send_json({"type": "report", "data": data})


async def _receive_stream(socket: WebSocket, runner: PipelineRunner) -> None:
    while True:
        message = await socket.receive()
        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(message.get("code", 1000))
        try:
            payload = json.loads(message.get("text", ""))
            if isinstance(payload, dict) and payload.get("type") == "reset":
                await asyncio.to_thread(runner.reset)
            else:
                logger.warning("Ignoring unsupported WebSocket message")
        except (ValueError, TypeError):
            logger.warning("Ignoring invalid WebSocket JSON")


def create_app(settings: Settings | None = None, runner: PipelineRunner | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        active = runner if runner is not None else build_default_runner(settings)
        app.state.runner = active
        try:
            await asyncio.to_thread(active.start)
            yield
        finally:
            await asyncio.to_thread(active.stop)

    app = FastAPI(lifespan=lifespan)
    if runner is not None:
        app.state.runner = runner
    app.add_middleware(CORSMiddleware,
                       allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                       allow_methods=["GET", "POST"], allow_headers=["*"])
    _register_routes(app)
    if settings.static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(settings.static_dir), html=True), name="frontend")
    return app


def _register_routes(app: FastAPI) -> None:
    @app.get("/api/health")
    async def health() -> dict:
        try:
            return {"success": True, "data": app.state.runner.health(), "error": None}
        except Exception as exc:
            logger.exception("Health lookup failed")
            return {"success": False, "data": None, "error": str(exc)}

    @app.get("/api/report")
    async def report() -> dict:
        try:
            latest = app.state.runner.latest_report()
            return {"success": True, "data": latest[1] if latest else None, "error": None}
        except Exception as exc:
            logger.exception("Report lookup failed")
            return {"success": False, "data": None, "error": str(exc)}

    @app.post("/api/reset")
    async def reset() -> dict:
        try:
            await asyncio.to_thread(app.state.runner.reset)
            return {"success": True, "data": {"reset": True}, "error": None}
        except Exception as exc:
            logger.exception("Pipeline reset failed")
            return {"success": False, "data": None, "error": str(exc)}

    @app.websocket("/ws/stream")
    async def stream(socket: WebSocket) -> None:
        await socket.accept()
        active = app.state.runner
        tasks: list[asyncio.Task] = []
        try:
            await socket.send_json({"type": "status", "data": active.health()})
            tasks = [asyncio.create_task(_send_stream(socket, active)),
                     asyncio.create_task(_receive_stream(socket, active))]
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        except WebSocketDisconnect:
            pass
        except RuntimeError:
            logger.debug("WebSocket closed", exc_info=True)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
