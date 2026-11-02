"""Settings, credentials and model prices."""
import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

# USD per million tokens (platform.claude.com/docs/en/about-claude/pricing, checked 31 Oct 2026)
PRICES = {
    "claude-haiku-5-5": dict(input=0.10, output=0.50, cache_write=0.125, cache_read=0.01),
    "claude-sonnet-5-5": dict(input=2.00, output=10.00, cache_write=2.50, cache_read=0.10),
    "claude-opus-5-5": dict(input=4.00, output=20.00, cache_write=5.00, cache_read=0.20),
}
DEFAULT_AGENT_MODEL = "claude-haiku-5-5"
DEFAULT_CRITIC_MODEL = "claude-haiku-5-5"


def load_env(path=None):
    """Read KEY=VALUE lines into os.environ. Accepts .env or a .env.txt saved by Notepad.
    Existing environment variables win."""
    candidates = [Path(path)] if path else [PROJECT / ".env"]
    candidates += [Path(str(c) + ".txt") for c in candidates]
    for c in candidates:
        if c.is_file():
            for line in c.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return c
    return None


def require_setting(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing setting {name}. Put '{name}=...' on its own line in your .env file "
                           f"and pass its location with --env.")
    return value


def cost_usd(model, usage):
    p = PRICES.get(model)
    if not p:
        return 0.0
    return (usage.get("input_tokens", 0) * p["input"] + usage.get("output_tokens", 0) * p["output"] +
            usage.get("cache_creation_input_tokens", 0) * p["cache_write"] +
            usage.get("cache_read_input_tokens", 0) * p["cache_read"]) / 1e6
