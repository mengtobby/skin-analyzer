"""Desktop service command line entry point."""
from __future__ import annotations

import argparse
from dataclasses import replace
import logging
import os
from pathlib import Path
import shutil
import subprocess  # nosec B404 - only launches the local Edge binary (list args, no shell)
import threading
import time
import urllib.request
import webbrowser

import uvicorn

from .api.app import _loopback, create_app
from .config import Settings
from .download_models import ensure_models

logger = logging.getLogger(__name__)


def _open_browser(url: str) -> None:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(120):
        try:
            with opener.open(url + "/api/health", timeout=1):
                break
        except OSError:
            time.sleep(0.5)
    else:
        logger.error("Server did not become ready; browser was not opened")
        return
    edge = shutil.which("msedge")
    if edge is None:
        for variable in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
            candidate = Path(os.environ.get(variable, "")) / "Microsoft/Edge/Application/msedge.exe"
            if candidate.is_file():
                edge = str(candidate)
                break
    try:
        if edge:
            # nosec B603: fixed Edge path found on disk + our own loopback URL; no shell
            subprocess.Popen([edge, f"--app={url}"],  # nosec B603
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        else:
            webbrowser.open(url)
    except OSError:
        logger.exception("Could not launch Edge; opening default browser")
        webbrowser.open(url)


def main() -> None:
    parser = argparse.ArgumentParser(description="Real-time skin analysis desktop service")
    parser.add_argument("--source")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--detector", choices=("auto", "classical", "onnx"))
    parser.add_argument("--preprocess", choices=("auto", "cpu", "cuda"))
    for name in ("width", "height", "fps", "jpeg-quality"):
        parser.add_argument(f"--{name}", type=int)
    parser.add_argument("--report-interval-s", type=float)
    parser.add_argument("--extra-origins", type=lambda raw: tuple(
        x.strip() for x in raw.split(",") if x.strip()))
    parser.add_argument("--no-mirror", action="store_true")
    parser.add_argument("--open", action="store_true", dest="open_browser")
    args = parser.parse_args()
    overrides = {key: getattr(args, key) for key in
                 ("source", "host", "port", "detector", "preprocess", "width", "height",
                  "fps", "jpeg_quality", "report_interval_s", "extra_origins") if getattr(args, key) is not None}
    if args.no_mirror:
        overrides["mirror"] = False
    settings = replace(Settings.from_env(), **overrides)
    logging.basicConfig(level=logging.INFO)
    if not _loopback(settings.host):
        logger.warning("CAMERA EXPOSED: binding to non-loopback host %s without authentication", settings.host)
    if settings.landmarker_model == Settings().landmarker_model:
        ensure_models(settings.landmarker_model.parent)
    if args.open_browser:
        # Detects a wildcard bind to open a loopback URL instead; does not bind to it.
        host = "127.0.0.1" if settings.host in {"0.0.0.0", "::"} else settings.host  # nosec B104
        threading.Thread(target=_open_browser, args=(f"http://{host}:{settings.port}",), daemon=True).start()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
