"""
Gemini로 유튜브 영상 자막 요약.

요약 포맷 (사장님 지정):
  - 한 줄 요약: 영상의 가장 핵심
  - 핵심 정리: 영상 흐름을 따라 빠짐 없이, 번호를 매기되 "핵심 한 줄 + 부연 설명" 구조
"""
import os

from google import genai

PROMPT = """너는 한국 주식·투자 유튜브 영상을 요약하는 전문 애널리스트야. 아래 영상의 자막을 읽고, 정확히 다음 구조로 한국어 요약을 작성해.

═══════════════════════════════
【한줄요약】
이 영상의 가장 핵심이 되는 메시지를 한 문장으로 압축. 두루뭉술하지 말고 구체적으로.

【핵심 정리】
영상의 논리 흐름을 따라가며, 빠뜨리는 부분 없이 모든 핵심 포인트를 추출.
각 포인트는 다음 형식:
1. (핵심 메시지 한 줄: 무엇을 말했는지 명확하게)
   - (그 한 줄을 풀어주는 부연 설명. 영상에서 든 근거·수치·예시·종목명 등 구체적인 내용 그대로 살려서 2~4줄)
2. (다음 핵심 메시지 한 줄)
   - (부연 설명)
…

규칙:
- 광고·자기소개·구독 부탁 같은 본문 외 부분은 무시.
- 종목명·수치·날짜·인물명은 자막에 나온 그대로 정확히 옮길 것 (요약하면서 바꾸지 마).
- 자막이 잘려 있거나 부정확해도, 들어 있는 내용으로만 요약. 추측 금지.
- 항목 개수는 영상 길이에 맞춰 자유롭게. 짧은 영상이면 3~5개, 긴 영상이면 7~12개.
═══════════════════════════════

영상 제목: {title}
채널: {channel_name}

자막:
{transcript}
"""


def summarize(
    transcript: str,
    title: str,
    channel_name: str,
    model: str = "gemini-2.5-flash",
) -> str:
    """자막을 받아 사장님이 지정한 포맷의 요약문 반환."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 환경변수가 없습니다.")

    client = genai.Client(api_key=api_key)
    prompt = PROMPT.format(
        title=title,
        channel_name=channel_name,
        transcript=transcript,
    )
    resp = client.models.generate_content(model=model, contents=prompt)
    text = (resp.text or "").strip()
    if not text:
        raise RuntimeError("Gemini 응답이 비었습니다.")
    return text
