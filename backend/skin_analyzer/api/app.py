"""FastAPI endpoints for the shared pipeline."""
from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ..config import Settings
from ..pipeline import PipelineRunner, build_default_runner

logger = logging.getLogger(__name__)


def _loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _health(runner: PipelineRunner) -> dict:
    data = dict(runner.health())
    if data.get("error"):
        logger.debug("Pipeline health error: %s", data["error"])
        data["error"] = "Pipeline unavailable"
    return data


async def _send_stream(socket: WebSocket, runner: PipelineRunner, event: asyncio.Event) -> None:
    packet_version = report_version = 0
    while True:
        await event.wait()
        event.clear()
        if not runner.is_running:
            await socket.close(code=1001)
            return
        packet = runner.latest_packet()
        if packet is not None and packet[0] > packet_version:
            packet_version, data = packet
            await socket.send_bytes(data)
        report = runner.latest_report()
        if report is not None and report[0] != report_version:
            report_version, data = report
            await socket.send_json({"type": "report", "data": data})


async def _receive_stream(socket: WebSocket, runner: PipelineRunner) -> None:
    invalid = 0
    last_log = float("-inf")
    while True:
        message = await socket.receive()
        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(message.get("code", 1000))
        text = message.get("text")
        if isinstance(text, str) and len(text.encode("utf-8")) > 1024:
            await socket.close(code=1009)
            return
        try:
            payload = json.loads(text) if isinstance(text, str) else None
        except ValueError:
            payload = None
        if isinstance(payload, dict) and payload.get("type") == "reset":
            await asyncio.to_thread(runner.reset)
            continue
        invalid += 1
        now = time.monotonic()
        if now - last_log >= 5:
            logger.debug("Ignoring invalid or unsupported WebSocket message")
            last_log = now
        if invalid >= 20:
            await socket.close(code=1003)
            return


async def _stream_session(socket: WebSocket, runner: PipelineRunner) -> None:
    loop = asyncio.get_running_loop()
    event = asyncio.Event()
    unsubscribe = runner.add_listener(lambda: loop.call_soon_threadsafe(event.set))
    tasks: list[asyncio.Task] = []
    try:
        await socket.send_json({"type": "status", "data": _health(runner)})
        event.set()
        tasks = [asyncio.create_task(_send_stream(socket, runner, event)),
                 asyncio.create_task(_receive_stream(socket, runner))]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket stream failed")
    finally:
        unsubscribe()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


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
    app.state.active_streams = 0
    app.state.allowed_origins = {
        "http://localhost:5173", "http://127.0.0.1:5173",
        f"http://localhost:{settings.port}", f"http://127.0.0.1:{settings.port}",
        *settings.extra_origins,
    }
    if runner is not None:
        app.state.runner = runner
    app.add_middleware(CORSMiddleware, allow_origins=list(app.state.allowed_origins),
                       allow_methods=["GET", "POST"], allow_headers=["*"])
    _register_routes(app)
    if settings.static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(settings.static_dir), html=True), name="frontend")
    return app


def _register_rest(app: FastAPI) -> None:
    @app.get("/api/health")
    async def health() -> dict:
        try:
            return {"success": True, "data": _health(app.state.runner), "error": None}
        except Exception:
            logger.exception("Health lookup failed")
            return {"success": False, "data": None, "error": "Health lookup failed"}

    @app.get("/api/report")
    async def report() -> dict:
        try:
            latest = app.state.runner.latest_report()
            return {"success": True, "data": latest[1] if latest else None, "error": None}
        except Exception:
            logger.exception("Report lookup failed")
            return {"success": False, "data": None, "error": "Report lookup failed"}

    @app.post("/api/reset", response_model=None)
    async def reset(request: Request) -> dict | JSONResponse:
        origin = request.headers.get("origin")
        if origin is not None and origin not in app.state.allowed_origins:
            return JSONResponse(status_code=403, content={
                "success": False, "data": None, "error": "Origin not allowed"})
        try:
            await asyncio.to_thread(app.state.runner.reset)
            return {"success": True, "data": {"reset": True}, "error": None}
        except Exception:
            logger.exception("Pipeline reset failed")
            return {"success": False, "data": None, "error": "Pipeline reset failed"}


def _register_routes(app: FastAPI) -> None:
    _register_rest(app)

    @app.websocket("/ws/stream")
    async def stream(socket: WebSocket) -> None:
        origin = socket.headers.get("origin")
        trusted = origin in app.state.allowed_origins if origin is not None else (
            socket.client is not None and _loopback(socket.client.host))
        if not trusted:
            await socket.close(code=1008)
            return
        if app.state.active_streams >= 8:
            await socket.close(code=1013)
            return
        app.state.active_streams += 1
        try:
            await socket.accept()
            await _stream_session(socket, app.state.runner)
        finally:
            app.state.active_streams -= 1
