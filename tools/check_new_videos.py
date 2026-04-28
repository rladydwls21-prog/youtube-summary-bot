"""
YouTube 채널 RSS 피드에서 최근 업로드 영상 목록 조회.
API key 없이 동작. RSS는 보통 채널의 최근 15개 영상을 노출.
"""
import xml.etree.ElementTree as ET
from urllib import request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}


def fetch_recent_videos(channel_id: str, limit: int = 15) -> list[dict]:
    """RSS에서 최근 영상 목록(최신순). 항목: video_id, title, published, url."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = request.Request(url, headers={"User-Agent": UA})
    with request.urlopen(req, timeout=20) as r:
        xml_text = r.read().decode("utf-8", errors="replace")

    root = ET.fromstring(xml_text)
    videos = []
    for entry in root.findall("atom:entry", NS):
        vid_el = entry.find("yt:videoId", NS)
        if vid_el is None or not vid_el.text:
            continue
        title_el = entry.find("atom:title", NS)
        published_el = entry.find("atom:published", NS)
        videos.append(
            {
                "video_id": vid_el.text,
                "title": (title_el.text or "(제목 없음)") if title_el is not None else "(제목 없음)",
                "published": (published_el.text or "") if published_el is not None else "",
                "url": f"https://www.youtube.com/watch?v={vid_el.text}",
            }
        )
        if len(videos) >= limit:
            break
    return videos
