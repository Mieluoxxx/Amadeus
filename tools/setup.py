#!/usr/bin/env python3
"""Amadeus tiered installer (cross-platform, uv-driven).

Tiers map to product capabilities:
  core        T1 conversation kernel (default) — chat/work/providers, no audio
  voice       T2 voice commons — playback, capture, AEC, barge-in (remote TTS ready)
  local-cu124 T2b local CUDA stack — embedded GPT-SoVITS/Qwen ASR (Windows lock)

Usage:
  python3 tools/setup.py [--tier core|voice|local-cu124] [--check] [--skip-electron]
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"

IS_WINDOWS = os.name == "nt"
IS_MACOS = sys.platform == "darwin"

TIERS = ("core", "voice", "local-cu124")
VOICE_BREW_DEPS = ("portaudio",)  # macOS: PyAudio builds against these


def log(msg: str) -> None:
    print(f"[setup] {msg}")


def fail(msg: str) -> None:
    print(f"[setup] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> int:
    log("$ " + " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, cwd=cwd or ROOT, env=env).returncode


def venv_python() -> Path:
    if IS_WINDOWS:
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python3"


def find_uv() -> str | None:
    return shutil.which("uv")


def ensure_uv() -> str:
    uv = find_uv()
    if uv:
        return uv
    fail(
        "uv not found. Install it first:\n"
        "  macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh\n"
        "  Windows:     winget install astral-sh.uv"
    )


def ensure_venv(uv: str) -> None:
    if venv_python().is_file():
        log(f"venv exists: {VENV}")
        return
    if run([uv, "venv", "--python", "3.12", str(VENV)]) != 0:
        fail("failed to create .venv (uv will fetch CPython 3.12 if missing)")


def install_python_deps(uv: str, tier: str) -> None:
    py = str(venv_python())
    if run([uv, "pip", "install", "--python", py, "-e", ".", "--no-deps"]) != 0:
        fail("editable install failed")

    if tier == "local-cu124" and IS_WINDOWS:
        # Windows CUDA tier stays on the pinned lock for reproducibility.
        if run([uv, "pip", "install", "--python", py, "-r", "requirements-cu124.txt"]) != 0:
            fail("local-cu124 lock install failed")
        return

    extras = {"core": "", "voice": "voice", "local-cu124": "voice,local-cu124"}[tier]
    if extras:
        if run([uv, "pip", "install", "--python", py, "-e", f".[{extras}]"]) != 0:
            fail(f"dependency install failed for tier {tier}")


def check_macos_voice() -> None:
    if not IS_MACOS:
        return
    brew = shutil.which("brew")
    missing = [d for d in VOICE_BREW_DEPS if not (brew and run_silent([brew, "list", d]))]
    if not missing:
        return
    if not brew:
        fail("voice tier on macOS requires Homebrew; then: brew install " + " ".join(missing))
    log("installing voice deps via brew: " + " ".join(missing))
    if run([brew, "install", *missing]) != 0:
        fail("brew install failed")


def install_electron(tier_env: dict) -> None:
    electron_dir = ROOT / "electron"
    npm = shutil.which("npm")
    if not npm:
        log("npm not found; skipping Electron frontend (install Node.js 22+ to enable it)")
        return
    if (electron_dir / "node_modules" / "electron" / "dist").exists():
        log("electron node_modules present; skipping npm ci")
    else:
        rc = run([npm, "ci"], cwd=electron_dir, env=tier_env)
        if rc != 0:
            log("npm ci failed; retrying with npmmirror Electron mirror")
            mirror_env = dict(tier_env, ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/")
            if run([npm, "ci"], cwd=electron_dir, env=mirror_env) != 0:
                fail("npm ci failed (also with mirror)")
    if run([npm, "run", "build"], cwd=electron_dir, env=tier_env) != 0:
        fail("electron build failed")


def bootstrap_env_file() -> None:
    env_file = ROOT / ".env"
    example = ROOT / ".env.example"
    if env_file.is_file():
        log(".env exists; leaving it untouched")
        return
    if example.is_file():
        shutil.copy(example, env_file)
        log(".env created from .env.example — fill in your API keys (DEEPSEEK_API_KEY etc.)")


def check() -> int:
    ok = True

    def row(name: str, good: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and good
        print(f"  [{'OK' if good else 'MISS'}] {name}{' — ' + detail if detail else ''}")

    print(f"[setup] environment check ({platform.system()} {platform.machine()})")
    row("uv", find_uv() is not None)
    row(".venv (python 3.12)", venv_python().is_file(), str(venv_python()))
    row("node", shutil.which("node") is not None)
    row("npm", shutil.which("npm") is not None)
    if IS_MACOS:
        brew = shutil.which("brew")
        row("portaudio (voice tier)", bool(brew) and run_silent([brew, "list", "portaudio"]))
    if venv_python().is_file():
        for mod, tier in (("fastapi", "core"), ("pyaudio", "voice"), ("torch", "local-cu124")):
            found = subprocess.run(
                [str(venv_python()), "-c", f"import {mod}"],
                capture_output=True,
            ).returncode == 0
            print(f"  [{'OK' if found else '  -'}] {mod} ({tier}) {'installed' if found else 'not installed'}")
    row(".env", (ROOT / ".env").is_file())
    return 0 if ok else 1


def run_silent(cmd: list[str]) -> bool:
    return subprocess.run(cmd, capture_output=True).returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Amadeus tiered installer")
    parser.add_argument("--tier", choices=TIERS, default="core")
    parser.add_argument("--check", action="store_true", help="report environment health only")
    parser.add_argument("--skip-electron", action="store_true")
    args = parser.parse_args()

    if args.check:
        return check()

    log(f"tier={args.tier} platform={platform.system()} python={platform.python_version()}")
    uv = ensure_uv()
    ensure_venv(uv)
    if args.tier in ("voice", "local-cu124"):
        check_macos_voice()
    install_python_deps(uv, args.tier)
    if not args.skip_electron:
        install_electron(dict(os.environ))
    bootstrap_env_file()
    log(f"done. Start with: {'run_electron_utf8.bat' if IS_WINDOWS else './run_electron_macos.sh'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
