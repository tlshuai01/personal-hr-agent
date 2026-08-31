#!/usr/bin/env python3
"""Refresh Boss 直聘 CLI 登录态（从浏览器 Cookie 或二维码）。

用法:
  python scripts/boss-login.py              # 默认从 Chrome 抽 Cookie
  python scripts/boss-login.py --browser edge
  python scripts/boss-login.py --qr         # 浏览器抽 Cookie 失败时用二维码
  python scripts/boss-login.py --verify-only
  python scripts/boss-login.py --c1         # 登录验证后跑 C1 dry-run

注意:
  - 默认 **不** 执行 logout（先 logout 再 login 有时会导致 Chrome Cookie 抽不到）
  - 请先在浏览器打开 zhipin.com 并保持已登录
  - Chrome 抽 Cookie 时建议关闭 Chrome，或确保 browser-cookie3 能读 Cookie DB
  - Edge 在 Windows 上可能需要管理员权限
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BROWSERS = ("chrome", "edge", "brave")


def resolve_boss_bin() -> str:
    env = os.environ.get("BOSS_CLI_BIN", "").strip()
    if env and Path(env).exists():
        return env
    found = shutil.which("boss")
    if found:
        return found
    win = Path.home() / "AppData/Local/Python/pythoncore-3.14-64/Scripts/boss.exe"
    if win.exists():
        return str(win)
    raise SystemExit(
        "找不到 boss CLI。请: pip install kabi-boss-cli，或设置 BOSS_CLI_BIN"
    )


def run(cmd: list[str], *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def parse_status(stdout: str) -> dict:
    text = stdout.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def try_browser_login(boss: str, browser: str) -> bool:
    print(f"→ boss login --cookie-source {browser}")
    proc = run([boss, "login", "--cookie-source", browser], timeout=120)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0 and ("登录成功" in out or "cookies" in out.lower()):
        print(f"  OK ({browser})")
        return True
    snippet = out.strip().splitlines()[-1] if out.strip() else f"exit {proc.returncode}"
    print(f"  skip ({browser}): {snippet[:120]}")
    return False


def try_qr_login(boss: str) -> bool:
    print("→ boss login (二维码，请在终端/App 完成扫码)")
    proc = subprocess.run([boss, "login"], env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return proc.returncode == 0


def verify(boss: str) -> dict:
    proc = run([boss, "status", "--json"], timeout=60)
    data = parse_status(proc.stdout)
    if proc.returncode != 0 and not data:
        print(proc.stderr or proc.stdout)
        raise SystemExit("boss status 失败")
    return data


def run_c1() -> int:
    main_py = ROOT / "main.py"
    venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    py = str(venv_py) if venv_py.exists() else sys.executable
    print("→ C1 dry-run: main.py --phase c1 --once --limit 3")
    return subprocess.call(
        [py, str(main_py), "--phase", "c1", "--once", "--limit", "3"],
        cwd=str(ROOT),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Boss CLI 登录封装")
    parser.add_argument(
        "--browser",
        action="append",
        dest="browsers",
        help=f"浏览器来源，可重复。默认: {', '.join(DEFAULT_BROWSERS)}",
    )
    parser.add_argument("--qr", action="store_true", help="浏览器失败后使用二维码登录")
    parser.add_argument(
        "--logout-first",
        action="store_true",
        help="先 logout（一般不需要，可能导致 Cookie 抽取失败）",
    )
    parser.add_argument("--verify-only", action="store_true", help="只检查 status，不登录")
    parser.add_argument("--c1", action="store_true", help="验证通过后跑 C1 dry-run")
    args = parser.parse_args()

    boss = resolve_boss_bin()
    print(f"boss: {boss}")

    if args.verify_only:
        status = verify(boss)
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0 if status.get("authenticated") else 1

    if args.logout_first:
        print("→ boss logout")
        run([boss, "logout"], timeout=30)

    browsers = args.browsers or list(DEFAULT_BROWSERS)
    ok = False
    for b in browsers:
        if try_browser_login(boss, b):
            ok = True
            break

    if not ok and args.qr:
        ok = try_qr_login(boss)

    status = verify(boss)
    print(json.dumps(status, ensure_ascii=False, indent=2))

    if not status.get("authenticated"):
        print(
            "\n登录未通过。建议:\n"
            "  1. 浏览器打开 https://www.zhipin.com 并确认已登录\n"
            "  2. 关闭 Chrome 后重试: python scripts/boss-login.py --browser chrome\n"
            "  3. 或使用二维码: python scripts/boss-login.py --qr\n"
            "  4. Edge 失败可忽略（Windows 常需管理员）",
            file=sys.stderr,
        )
        return 1

    print("\n✓ Boss 登录态有效")
    if args.c1:
        return run_c1()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
