#!/usr/bin/env python3
"""从浏览器 Cookie 登录 Boss CLI（**不用二维码**）。

前提：你已在浏览器里登录 https://www.zhipin.com

步骤:
  1. Chrome 登录 zhipin.com 后 **完全退出 Chrome**（任务管理器确认无 chrome.exe）
  2. python scripts/boss-login-cookie.py
  3. python scripts/boss-login-cookie.py --verify-only

若用 Edge 登录 Boss：PowerShell **管理员** 运行:
  python scripts/boss-login-cookie.py --browser edge
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REQUIRED = {"__zp_stoken__", "wt2", "wbg", "zp_at"}
CONFIG_DIR = Path.home() / ".config" / "boss-cli"
CREDENTIAL_FILE = CONFIG_DIR / "credential.json"


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
    raise SystemExit("找不到 boss.exe，请先: pip install kabi-boss-cli")


def python_for_cookie() -> str:
    boss = resolve_boss_bin()
    boss_py = Path(boss).resolve().parent.parent / "python.exe"
    if boss_py.is_file():
        return str(boss_py)
    return sys.executable


def extract_cookies(browser: str) -> tuple[str, dict[str, str]] | None:
    import browser_cookie3 as bc3

    loaders = {
        "chrome": bc3.chrome,
        "edge": bc3.edge,
        "brave": bc3.brave,
        "firefox": bc3.firefox,
    }
    loader = loaders.get(browser.lower())
    if not loader:
        raise SystemExit(f"不支持的浏览器: {browser}")

    try:
        cj = loader(domain_name=".zhipin.com")
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        print(f"  读取失败 ({browser}): {err}")
        if browser.lower() == "edge" and "decryption" in str(exc).lower():
            print(
                "  [edge] Windows 常因 Cookie 加密密钥读不到而失败。\n"
                "       建议: 用 Chrome 登录 zhipin → 退出 Chrome → 不加 --browser edge\n"
                "       或: 管理员 PowerShell 再试 edge（仍不如 Chrome 稳）"
            )
        elif browser.lower() == "chrome" and "decryption" in str(exc).lower():
            print(
                "  [chrome] 请完全退出 Chrome（任务管理器无 chrome.exe）后重试"
            )
        return None

    cookies = {c.name: c.value for c in cj if "zhipin.com" in (c.domain or "")}
    if not cookies:
        print(f"  {browser}: 未找到 zhipin.com Cookie")
        return None

    missing = REQUIRED - set(cookies)
    if missing:
        print(f"  {browser}: Cookie 不全，缺少 {sorted(missing)}（请在浏览器重新登录 zhipin）")
        return None

    return browser, cookies


def save_credential(cookies: dict[str, str]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"cookies": cookies, "saved_at": time.time()}
    CREDENTIAL_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  已写入 {CREDENTIAL_FILE}")


def verify_boss(boss: str) -> dict:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    proc = subprocess.run(
        [boss, "status", "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=90,
    )
    text = (proc.stdout or proc.stderr or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text, "exit": proc.returncode}


def main() -> int:
    parser = argparse.ArgumentParser(description="从浏览器 Cookie 登录（无二维码）")
    parser.add_argument(
        "--browser",
        action="append",
        dest="browsers",
        help="chrome / edge / brave / firefox，可多次指定",
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    boss = resolve_boss_bin()
    print(f"boss: {boss}")

    if args.verify_only:
        status = verify_boss(boss)
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0 if status.get("authenticated") else 1

    browsers = args.browsers or ["chrome", "brave", "firefox"]
    print("提示: 请先完全关闭 Chrome/Edge 再抽 Cookie\n")

    for b in browsers:
        print(f"→ 尝试 {b} ...")
        got = extract_cookies(b)
        if not got:
            continue
        name, cookies = got
        save_credential(cookies)
        print(f"  从 {name} 提取 {len(cookies)} 个 Cookie")
        status = verify_boss(boss)
        print(json.dumps(status, ensure_ascii=False, indent=2))
        if status.get("authenticated"):
            print("\n✓ 登录成功，可跑 dry-run")
            return 0
        print("\n⚠ Cookie 已保存但 API 校验未通过，请在浏览器重新打开 zhipin.com 登录后再试")
        return 1

    print(
        "\n全部失败。请检查:\n"
        "  1. 浏览器已登录 https://www.zhipin.com\n"
        "  2. 已完全关闭 Chrome（任务管理器无 chrome.exe）\n"
        "  3. Edge 用户: 管理员 PowerShell + --browser edge\n"
        "  4. 勿使用 F12 抄 Cookie；Boss 有反调试",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
