"""
state.json 읽기/쓰기.

채널별로 마지막으로 처리한 video_id를 기억해서, 다음 실행 때 그 이후의 영상만 새 영상으로 인식.
state.json은 git에 commit되어 GitHub Actions 실행 사이에도 유지됨.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "state.json"


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    text = STATE_PATH.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    return json.loads(text)


def save_state(state: dict) -> None:
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
