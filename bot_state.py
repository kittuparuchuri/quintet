"""Global bot state, stored in a tiny file so it survives restarts."""
import json, pathlib

STATE_FILE = pathlib.Path("bot_state.json")
RUNNING, HALTED = "RUNNING", "HALTED"

def get_state() -> str:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text()).get("state", RUNNING)
    return RUNNING

def set_state(state: str):
    STATE_FILE.write_text(json.dumps({"state": state}))
