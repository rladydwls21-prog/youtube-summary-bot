"""
YouTube Data API v3로 채널 최근 업로드 영상 조회.

이전엔 무료 RSS 피드(/feeds/videos.xml)를 썼지만 2026-04-29경부터 글로벌하게
404를 반환하기 시작해 공식 API로 전환. playlistItems.list 호출당 1 unit, 일일
무료 할당량 10,000 unit이라 채널 수십 개를 매시간 돌려도 여유 있음.
"""
import json
import os
from urllib import error, parse, request

API_BASE = "https://www.googleapis.com/youtube/v3"


def _uploads_playlist_id(channel_id: str) -> str:
    # YouTube 규약: 채널 ID 'UCxxx'의 업로드 재생목록은 항상 'UUxxx'.
    if not channel_id.startswith("UC"):
        raise ValueError(f"예상 못 한 channel_id 형식: {channel_id}")
    return "UU" + channel_id[2:]


def fetch_recent_videos(channel_id: str, limit: int = 15) -> list[dict]:
    """채널 최근 업로드(최신순). 항목: video_id, title, published, url."""
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY 환경변수가 없습니다")

    params = {
        "part": "snippet,contentDetails",
        "playlistId": _uploads_playlist_id(channel_id),
        "maxResults": str(min(limit, 50)),
        "key": api_key,
    }
    url = f"{API_BASE}/playlistItems?{parse.urlencode(params)}"

    try:
        with request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"YouTube API HTTP {e.code}: {body[:300]}") from e

    videos = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        content = item.get("contentDetails", {})
        video_id = content.get("videoId") or snippet.get("resourceId", {}).get("videoId")
        if not video_id:
            continue
        videos.append(
            {
                "video_id": video_id,
                "title": snippet.get("title", "(제목 없음)"),
                "published": content.get("videoPublishedAt") or snippet.get("publishedAt", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
        )
    return videos
