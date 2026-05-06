# Workflow: 유튜브 새 영상 자동 요약 → 텔레그램 발송

## 목표
선별한 주식·투자 유튜버들의 새 영상이 올라올 때마다 자동 감지 → Gemini로 요약 → 사장님 텔레그램 봇 채팅방에 전달.

## 실행 주기
GitHub Actions가 **매시 7분(UTC)**에 자동 실행. 한국 시간 기준으로도 매시간 한 번 돌아감.
수동 실행도 가능: GitHub repo → Actions 탭 → "YouTube Summary Bot" → "Run workflow".

## 입력
- `channels.json` — 감시할 유튜버 목록(채널명, handle, URL, channel_id).
- `state.json` — 채널별 마지막으로 처리한 video_id (자동 갱신).
- 환경변수 — `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. 로컬은 `.env`, Actions는 GitHub Secrets.

## 처리 흐름
1. `channels.json`을 읽어 모든 채널을 순회.
2. 각 채널에 대해:
   1. **RSS 조회** (`tools/check_new_videos.py`) — 최근 15개 영상.
   2. **첫 등록 채널이면**: 가장 최신 영상의 ID만 `state.json`에 기록하고 종료(요약 발송 X). → 첫 실행 때 수십 개 영상이 한꺼번에 텔레그램으로 쏟아지는 사고 방지.
   3. **이전 마지막 영상 이후의 새 영상**만 추려, 오래된 순으로 처리:
      1. **쇼츠 판별** (`tools/check_new_videos.py::is_short`) — `youtube.com/shorts/<id>` HEAD 요청 결과 200이면 쇼츠로 간주, 요약 없이 건너뛰고 state만 갱신해 다음 실행에 재검사 안 함. 사장님이 쇼츠는 안 보기로 결정(2026-05-07).
      2. **자막 추출** (`tools/get_transcript.py`) — 한국어 자막 우선, 없으면 영어, 그것도 없으면 자동 생성 자막.
      3. **요약 생성** (`tools/summarize_with_gemini.py`) — Gemini-2.5-flash, "한줄요약 + 번호 매긴 핵심정리" 포맷.
      4. **텔레그램 발송** (`tools/send_to_telegram.py`) — 4096자 넘으면 자동 분할.
      5. **state 갱신** — 발송 성공 시점에 즉시 갱신(중간에 죽어도 진행 상황 보존).
   4. 자막을 못 가져온 영상은 "자막 없음" 알림만 발송, 사장님이 직접 보러 갈 수 있게 링크 첨부.
3. `state.json` 저장.
4. (Actions에서) 변경된 `state.json`을 자동 commit & push.

## 채널 추가/삭제
1. `channels.json`에 새 항목 추가 (channel_id는 빈 문자열로 두면 됨).
2. `python tools/extract_channel_ids.py` 실행 → channel_id 자동 채워짐.
3. commit & push. 다음 실행부터 새 채널이 모니터링됨.

## 실패 처리 원칙
- 한 채널이 깨져도 다른 채널은 계속 진행.
- 한 영상이 깨져도 다음 영상은 계속 진행. 단, 깨진 영상의 state는 갱신 안 함 → 다음 실행에 자동 재시도.
- Actions가 1시간 넘게 멈춰 있으면 GitHub이 빨간 X 표시 → 사장님이 메일로 알림 받음.

## 비용
- Gemini API: 무료 tier 안에서 운영 (영상 1개당 자막 길이 따라 다르지만 7명 채널 정도면 무료 한도 안).
- GitHub Actions: private repo 월 2,000분 무료. 매시간 2분 × 24 × 30 = 1,440분 → 무료.
- 텔레그램: 무료.
- YouTube RSS: 무료, API key 불필요.
