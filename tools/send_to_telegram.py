"""
텔레그램 봇으로 메시지 발송.
4096자 제한 자동 분할 (가능하면 줄 단위로 자름).
"""
import json
import os
from urllib import request
from urllib.parse import urlencode

TELEGRAM_LIMIT = 4096


def split_chunks(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    buf = ""
    for line in text.split("\n"):
        # 한 줄이 limit보다 긴 경우 강제 분할
        while len(line) > limit:
            if buf:
                chunks.append(buf.rstrip("\n"))
                buf = ""
            chunks.append(line[:limit])
            line = line[limit:]
        # 누적 buf에 line을 추가하면 limit을 넘는 경우, buf를 flush하고 새로 시작
        if len(buf) + len(line) + 1 > limit:
            if buf:
                chunks.append(buf.rstrip("\n"))
            buf = line + "\n"
        else:
            buf += line + "\n"
    if buf.strip():
        chunks.append(buf.rstrip("\n"))
    return chunks


def send_message(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID 환경변수가 없습니다.")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chunk in split_chunks(text):
        payload = urlencode(
            {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": "false",
            }
        ).encode()
        req = request.Request(url, data=payload, method="POST")
        with request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        if not data.get("ok"):
            raise RuntimeError(f"Telegram send failed: {data}")
