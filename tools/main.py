"""
메인 엔트리: 모든 채널의 새 영상을 감지 → 자막 추출 → Gemini 요약 → 텔레그램 발송 → state 갱신.

GitHub Actions에서 매시간 실행됨. 로컬에서 수동 실행도 가능.
"""
import json
import os
import sys
import traceback
from pathlib import Path

# Windows 콘솔 한글 깨짐 방지 (로컬 실행시; Actions의 Linux는 영향 없음)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from tools.check_new_videos import fetch_recent_videos  # noqa: E402
from tools.get_transcript import get_transcript  # noqa: E402
from tools.send_to_telegram import send_message  # noqa: E402
from tools.state import load_state, save_state  # noqa: E402
from tools.summarize_with_gemini import summarize  # noqa: E402

REQUIRED_ENV = ("GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")


def load_channels() -> list[dict]:
    return json.loads((ROOT / "channels.json").read_text(encoding="utf-8"))


def format_message(channel_name: str, video: dict, summary: str) -> str:
    return (
        f"📺 [{channel_name}] {video['title']}\n"
        f"🔗 {video['url']}\n\n"
        f"{summary}"
    )


def format_no_transcript(channel_name: str, video: dict) -> str:
    return (
        f"📺 [{channel_name}] {video['title']}\n"
        f"🔗 {video['url']}\n\n"
        "⚠️ 이 영상은 자막을 가져올 수 없어 요약을 생성하지 못했습니다.\n"
        "(자막 비활성화/지역 제한/실시간 송출 직후 등)"
    )


def process_channel(channel: dict, state: dict) -> int:
    cid = channel["channel_id"]
    name = channel["name"]
    print(f"\n[{name}] RSS 조회...", flush=True)

    try:
        videos = fetch_recent_videos(cid, limit=15)
    except Exception as e:
        print(f"  [ERROR] RSS 조회 실패: {e}")
        return 0

    if not videos:
        print("  최근 영상 없음")
        return 0

    last_id = state.get(cid, {}).get("last_video_id")

    # 첫 등록: 가장 최근 영상 ID만 기록, 요약은 건너뜀 (수십 개 영상이 한꺼번에 쏟아지는 것 방지)
    if last_id is None:
        latest = videos[0]
        state[cid] = {
            "last_video_id": latest["video_id"],
            "last_published": latest["published"],
        }
        print(f"  [첫 등록] 기준점만 기록: {latest['title'][:50]}")
        return 0

    new_videos = []
    for v in videos:
        if v["video_id"] == last_id:
            break
        new_videos.append(v)

    if not new_videos:
        print("  새 영상 없음")
        return 0

    new_videos.reverse()  # 오래된 → 최신 순으로 발송
    print(f"  새 영상 {len(new_videos)}개 발견")

    sent = 0
    for v in new_videos:
        print(f"  → 처리: {v['title'][:60]}", flush=True)
        try:
            transcript = get_transcript(v["video_id"])
        except Exception as e:
            print(f"    자막 추출 예외: {e}")
            transcript = None

        try:
            if transcript:
                summary = summarize(transcript, v["title"], name)
                msg = format_message(name, v, summary)
            else:
                msg = format_no_transcript(name, v)
            send_message(msg)
            sent += 1
            # 한 영상 성공할 때마다 state 갱신 (중간에 죽어도 진행 상황 보존)
            state[cid] = {"last_video_id": v["video_id"], "last_published": v["published"]}
        except Exception as e:
            print(f"    요약/발송 실패: {e}")
            traceback.print_exc()
            # 다음 영상은 시도. state는 갱신 안 함 → 다음 실행에 재시도
            continue

    return sent


def main() -> int:
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        print(f"[ERROR] 환경변수 누락: {missing}")
        return 1

    channels = load_channels()
    state = load_state()

    total_sent = 0
    for ch in channels:
        if not ch.get("channel_id"):
            print(f"[WARN] {ch['name']}: channel_id 없음 → 건너뜀")
            continue
        try:
            total_sent += process_channel(ch, state)
        except Exception as e:
            print(f"[ERROR] {ch['name']} 처리 중 예외: {e}")
            traceback.print_exc()

    save_state(state)
    print(f"\n[DONE] 총 발송 메시지 수: {total_sent}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
