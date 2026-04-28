"""
Gemini로 유튜브 영상 요약. 두 가지 입력 모드:
  1) summarize(transcript, ...)             — 자막 텍스트로 요약 (저비용, 1차)
  2) summarize_from_video_url(url, ...)     — Gemini가 YouTube URL을 직접 받아
                                              영상/오디오/자막을 통합 분석 (자막 추출이
                                              막혔을 때의 fallback)

요약 포맷 (사장님 지정):
  - 한 줄 결론 + 번호 매긴 핵심 정리 (~임/~함/명사 종결, 키캡 이모지)
"""
import os

from google import genai
from google.genai import types

PROMPT = """너는 한국 주식·투자 유튜브 영상을 요약하는 전문 애널리스트야. 아래 영상의 자막을 읽고, 다음 출력 형식과 규칙을 *정확히* 지켜 한국어 요약을 작성해.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
【출력 형식 — 이대로 그대로】

🔥한 줄 결론🔥
이 영상에서 시청자가 가장 기억해야 할 메시지를 한 문장으로. 두루뭉술 X, 구체적으로. 반드시 ~임/~함/~됨 또는 명사로 끝낼 것.

🚨핵심 요약🚨

1️⃣ 첫 번째 핵심 메시지의 짧은 제목
- 짧고 단단한 한 줄 사실
- 또 다른 사실 한 줄
- (필요 시) 구체 예시·수치·종목명 한 줄

2️⃣ 두 번째 핵심 메시지의 짧은 제목
- 한 줄
- 한 줄

3️⃣ …

(항목은 영상 길이에 맞춰 4~7개. 너무 많으면 핵심 흐려짐.)
━━━━━━━━━━━━━━━━━━━━━━━━━━━

【반드시 지킬 규칙 — 어기면 무효】

1. 항목 번호는 반드시 1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣ 키캡 이모지 숫자만 사용. `1.` `①` 같은 다른 형식 절대 금지.
2. 1️⃣ 옆 제목에 **괄호를 붙이지 말 것.** (OK 예시: `1️⃣ 글로벌 자금 흐름 파악` / 금지: `1️⃣ (글로벌 자금 흐름 파악)`)
3. 문장 종결은 모두 음슴체(~임/~함/~됨/~필요함) 또는 **명사로 끝**. 평서문체(~다/~합니다/~입니다) 절대 금지.
4. 부연 줄은 들여쓰기 없이 줄 첫머리에 `- ` 하이픈+공백으로 시작.
5. 각 부연은 한 줄에 한 사실만. 두루뭉술한 표현·중복·추상어 금지.
6. 영상에 등장한 종목명·티커·수치·기관명·인물명은 자막 그대로 정확히 옮길 것. 임의 변환 금지.
7. 항목 사이에는 빈 줄 1개씩.
8. 1️⃣ 2️⃣ 3️⃣ … 옆 제목들만 쭉 읽었을 때 영상 전체의 줄거리가 잡혀야 함. 제목은 그 자체로 자기완결성 있게.
9. 광고·자기소개·구독 부탁·인사말은 모두 무시.
9.5. 어떤 종류의 마크다운(**굵게**, *기울임*, _밑줄_, `코드`)도 사용 금지. 일반 텍스트만 출력. 강조하고 싶으면 키캡 이모지나 줄바꿈으로.
10. 자막에 없는 내용은 절대 추측해서 쓰지 말 것.

━━━━━━━━━━━━━━━━━━━━━━━━━━━

영상 제목: {title}
채널: {channel_name}

자막:
{transcript}
"""


PROMPT_FROM_VIDEO = """너는 한국 주식·투자 유튜브 영상을 요약하는 전문 애널리스트야. 위에 첨부된 유튜브 영상을 끝까지 시청한 뒤, 다음 출력 형식과 규칙을 *정확히* 지켜 한국어 요약을 작성해.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
【출력 형식 — 이대로 그대로】

🔥한 줄 결론🔥
이 영상에서 시청자가 가장 기억해야 할 메시지를 한 문장으로. 두루뭉술 X, 구체적으로. 반드시 ~임/~함/~됨 또는 명사로 끝낼 것.

🚨핵심 요약🚨

1️⃣ 첫 번째 핵심 메시지의 짧은 제목
- 짧고 단단한 한 줄 사실
- 또 다른 사실 한 줄
- (필요 시) 구체 예시·수치·종목명 한 줄

2️⃣ 두 번째 핵심 메시지의 짧은 제목
- 한 줄
- 한 줄

3️⃣ …

(항목은 영상 길이에 맞춰 4~7개. 너무 많으면 핵심 흐려짐.)
━━━━━━━━━━━━━━━━━━━━━━━━━━━

【반드시 지킬 규칙 — 어기면 무효】

1. 항목 번호는 반드시 1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣ 키캡 이모지 숫자만 사용. `1.` `①` 같은 다른 형식 절대 금지.
2. 1️⃣ 옆 제목에 **괄호를 붙이지 말 것.**
3. 문장 종결은 모두 음슴체(~임/~함/~됨/~필요함) 또는 **명사로 끝**. 평서문체(~다/~합니다/~입니다) 절대 금지.
4. 부연 줄은 들여쓰기 없이 줄 첫머리에 `- ` 하이픈+공백으로 시작.
5. 각 부연은 한 줄에 한 사실만. 두루뭉술한 표현·중복·추상어 금지.
6. 영상에 등장한 종목명·티커·수치·기관명·인물명은 영상에서 들리는 대로 정확히 옮길 것. 임의 변환 금지.
7. 항목 사이에는 빈 줄 1개씩.
8. 1️⃣ 2️⃣ 3️⃣ … 옆 제목들만 쭉 읽었을 때 영상 전체의 줄거리가 잡혀야 함.
9. 광고·자기소개·구독 부탁·인사말은 모두 무시.
9.5. 어떤 종류의 마크다운(**굵게**, *기울임*, _밑줄_, `코드`)도 사용 금지. 일반 텍스트만 출력. 강조하고 싶으면 키캡 이모지나 줄바꿈으로.
10. 영상에서 확인할 수 없는 내용은 절대 추측해서 쓰지 말 것.

━━━━━━━━━━━━━━━━━━━━━━━━━━━

영상 제목: {title}
채널: {channel_name}
"""


def summarize(
    transcript: str,
    title: str,
    channel_name: str,
    model: str = "gemini-2.5-flash",
) -> str:
    """자막을 받아 사장님이 지정한 포맷의 요약문 반환. (1차 경로 — 저비용)"""
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


def summarize_from_video_url(
    video_url: str,
    title: str,
    channel_name: str,
    model: str = "gemini-2.5-flash",
) -> str:
    """YouTube URL을 Gemini에 직접 넘겨 영상 분석으로 요약. (2차 fallback)

    자막이 추출 안 될 때(예: GitHub Actions IP 차단)도 작동.
    Gemini가 영상의 음성·시각·자막을 통합 분석.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 환경변수가 없습니다.")

    client = genai.Client(api_key=api_key)
    prompt = PROMPT_FROM_VIDEO.format(
        title=title,
        channel_name=channel_name,
    )

    contents = types.Content(
        parts=[
            types.Part(file_data=types.FileData(file_uri=video_url)),
            types.Part(text=prompt),
        ]
    )
    resp = client.models.generate_content(model=model, contents=contents)
    text = (resp.text or "").strip()
    if not text:
        raise RuntimeError("Gemini 영상 분석 응답이 비었습니다.")
    return text
