"""
채널 URL → channel_id 추출 도구.

사용 시점: 새 유튜버를 channels.json에 추가했을 때 한 번 돌림.
동작: channels.json을 읽어 channel_id가 비어 있는 항목만 채워서 저장.

사용법:
  .venv/Scripts/python.exe tools/extract_channel_ids.py
"""
import json
import re
import sys
from pathlib import Path
from urllib import request, error

sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# YouTube 채널 페이지 HTML에서 channel_id를 뽑아내는 패턴.
# 페이지 구조가 가끔 바뀌므로 후보 패턴을 여러 개 둠.
PATTERNS = [
    r'"channelId":"(UC[A-Za-z0-9_-]{22})"',
    r'"externalId":"(UC[A-Za-z0-9_-]{22})"',
    r'<meta itemprop="identifier"\s+content="(UC[A-Za-z0-9_-]{22})"',
    r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[A-Za-z0-9_-]{22})"',
]


def fetch_channel_id(url: str) -> str | None:
    req = request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko,en;q=0.9"})
    try:
        with request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="replace")
    except error.HTTPError as e:
        print(f"  [HTTP {e.code}] {url}")
        return None
    except Exception as e:
        print(f"  [ERROR] {type(e).__name__}: {e}")
        return None

    for pat in PATTERNS:
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return None


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    channels_path = root / "channels.json"
    if not channels_path.exists():
        print(f"[ERROR] {channels_path} 없음")
        return 1

    channels = json.loads(channels_path.read_text(encoding="utf-8"))
    updated = False
    failed = []

    for ch in channels:
        if ch.get("channel_id"):
            continue
        print(f"[조회] {ch['name']:20s}  {ch['url']}")
        cid = fetch_channel_id(ch["url"])
        if cid:
            ch["channel_id"] = cid
            print(f"        → {cid}")
            updated = True
        else:
            print(f"        → 추출 실패")
            failed.append(ch["name"])

    if updated:
        channels_path.write_text(
            json.dumps(channels, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("\n[OK] channels.json 업데이트 완료")

    if failed:
        print(f"\n[WARN] 실패한 채널: {failed}")
        print("       URL이 정확한지 확인하거나, 직접 channel_id를 channels.json에 적어 넣어주세요.")
        return 2

    print("[OK] 모든 채널 channel_id 확보 완료.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
