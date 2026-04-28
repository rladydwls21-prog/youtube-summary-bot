"""
유튜브 영상 자막(transcript) 추출.

전략:
  1) 한국어 수동/공식 자막 → 가장 신뢰도 높음
  2) 한국어 자동 생성 자막 → 보통 잘 됨
  3) 영어 자막 (한국어가 전혀 없을 때만)
  4) 다 실패하면 None 반환 → 호출 측에서 "자막 없음" 메시지 처리
"""
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi

PREFERRED_LANGS = ["ko", "ko-KR", "en", "en-US"]


def _join_snippets(snippets) -> str:
    """라이브러리 버전에 따라 dict 또는 객체로 옴. 둘 다 처리."""
    parts = []
    for s in snippets:
        if isinstance(s, dict):
            t = s.get("text", "")
        else:
            t = getattr(s, "text", "") or ""
        t = t.strip()
        if t:
            parts.append(t)
    return " ".join(parts)


def get_transcript(video_id: str) -> Optional[str]:
    """자막 텍스트(한 줄로 이어붙임). 자막 없으면 None."""
    # 신/구 API 모두 호환되도록 두 가지 경로 시도
    try:
        # 0.6.x 스타일
        snippets = YouTubeTranscriptApi.get_transcript(video_id, languages=PREFERRED_LANGS)
        text = _join_snippets(snippets)
        return text or None
    except AttributeError:
        # 신 API (0.7+)
        try:
            api = YouTubeTranscriptApi()
            fetched = api.fetch(video_id, languages=PREFERRED_LANGS)
            snippets = fetched if isinstance(fetched, list) else getattr(fetched, "snippets", [])
            text = _join_snippets(snippets)
            return text or None
        except Exception:
            return None
    except Exception:
        # 자막 비활성/없음/사용불가
        return None
