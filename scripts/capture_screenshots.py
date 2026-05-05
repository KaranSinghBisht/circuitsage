"""Capture CircuitSage screenshots for the Kaggle writeup and gallery.

Run after the backend (port 8000) and frontend (port 5173) are up.
Re-runs `make demo-seed` first so Educator + Faults render meaningful aggregates.

Run:
    backend/.venv/bin/python scripts/capture_screenshots.py
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "media" / "screenshots"
FRONTEND = "http://127.0.0.1:5173"
BACKEND = "http://127.0.0.1:8000"
VIEWPORT = {"width": 1440, "height": 900}


async def _seed_op_amp_session() -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        for _ in range(20):
            try:
                response = await client.post(f"{BACKEND}/api/sessions/seed/op-amp")
                response.raise_for_status()
                return response.json()["id"]
            except (httpx.ConnectError, httpx.ReadError):
                await asyncio.sleep(1)
        raise RuntimeError("backend never came up")


async def _wait_for(url: str, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    async with httpx.AsyncClient(timeout=5.0) as client:
        while time.time() < deadline:
            try:
                response = await client.get(url)
                if response.status_code < 500:
                    return
            except (httpx.ConnectError, httpx.ReadError):
                pass
            await asyncio.sleep(1)
    raise RuntimeError(f"{url} never came up")


async def _shoot(page, route: str, name: str, settle: float = 1.5) -> Path:
    target = OUT / f"{name}.png"
    await page.goto(f"{FRONTEND}{route}", wait_until="networkidle")
    await asyncio.sleep(settle)
    await page.screenshot(path=str(target), full_page=False)
    print(f"shot {name} -> {target}")
    return target


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("waiting for frontend at", FRONTEND)
    await _wait_for(FRONTEND, timeout=90)
    print("waiting for backend health")
    await _wait_for(f"{BACKEND}/api/health", timeout=60)
    print("seeding op-amp session")
    session_id = await _seed_op_amp_session()
    print("session:", session_id)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport=VIEWPORT, color_scheme="dark")
        page = await context.new_page()

        await _shoot(page, "/", "01_home")
        await _shoot(page, f"/studio/{session_id}", "02_studio")
        await _shoot(page, f"/bench/{session_id}", "03_bench")
        await _shoot(page, "/companion", "04_companion")
        await _shoot(page, "/faults", "05_faults")
        await _shoot(page, "/educator", "06_educator")
        await _shoot(page, "/uncertainty", "07_uncertainty")
        await _shoot(page, "/press", "08_press")

        await browser.close()
    print("done. output:", OUT)


if __name__ == "__main__":
    asyncio.run(main())
