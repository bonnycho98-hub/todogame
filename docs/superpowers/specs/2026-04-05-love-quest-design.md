# LOVE QUEST — 설계 문서

**작성일**: 2026-04-05  
**상태**: 확정

---

## 1. 개요

할일 관리 프로그램을 게임 퀘스트 형태로 구현한다. 전체 목표는 "나 자신을 사랑하기"이며, "나를 사랑하기"와 "타인을 사랑하기" 두 갈래로 나뉜다. 퀘스트를 완료하면 NPC 친밀도가 오르고, 이것이 인생 행복 확률로 시각화된다.

---

## 2. 인프라

| 항목 | 선택 | 이유 |
|---|---|---|
| 언어/프레임워크 | Python + FastAPI | 텔레그램 봇 생태계 최적, 단순함 |
| 데이터베이스 | PostgreSQL | Railway 무료 티어 포함 |
| 배포 | Railway 무료 티어 | 단일 서버로 웹+봇 동시 운용 |
| 프론트엔드 | Vanilla HTML/CSS/JS | FastAPI에서 직접 서빙, 의존성 최소화 |
| 아키텍처 | 모노리스 | 웹서버 + 텔레그램 봇 + DB를 단일 프로세스로 |

---

## 3. 게임 구조

```
전체 목표: 나 자신을 사랑하기
│
├── 나를 사랑하기 (self)
│   └── 퀘스트 N개
│       ├── daily (루틴 설정)
│       ├── one-time
│       └── 서브태스크 목록
│
└── 타인을 사랑하기 (others)
    └── NPC 1..N 명 (사용자가 직접 추가)
        ├── 캐릭터 (5줄 특수문자, 랜덤 생성)
        ├── 니즈 목록 (사용자가 직접 입력)
        │   └── [니즈] → 연결된 퀘스트들
        │       └── [퀘스트] → 서브태스크들
        └── 친밀도 (0~∞, 누적)
```

---

## 4. 데이터 모델

### npcs
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID | PK |
| name | TEXT | NPC 이름 |
| relationship | TEXT | 관계 유형 (가족, 친구 등) |
| sprite | TEXT | 5줄 특수문자 아트 |
| color | TEXT | 캐릭터 색상 (hex) |
| created_at | TIMESTAMP | |

### needs (NPC 니즈)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID | PK |
| npc_id | UUID | FK → npcs (NULL이면 self) |
| title | TEXT | 니즈 내용 |
| created_at | TIMESTAMP | |

### quests
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID | PK |
| need_id | UUID | FK → needs (NULL이면 self 직접 퀘스트) |
| title | TEXT | 퀘스트 제목 |
| quest_type | ENUM | `daily` / `one_time` |
| routine | JSONB | 루틴 설정 (아래 참조) |
| intimacy_reward | INT | 완료 시 친밀도 증가량 (누적, 상한 없음) |
| is_archived | BOOL | 완료된 one-time 퀘스트 보관 |
| created_at | TIMESTAMP | |

**routine JSONB 구조:**
```json
// 매일
{ "type": "daily" }

// 매주 특정 요일 (0=월, 6=일)
{ "type": "weekly", "days": [0, 2, 4] }

// 매월 특정 날짜
{ "type": "monthly", "dates": [1, 15] }
```

### subtasks
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID | PK |
| quest_id | UUID | FK → quests |
| title | TEXT | 서브태스크 내용 |
| order | INT | 표시 순서 |

### daily_completions (일일 미션 완료 기록)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID | PK |
| subtask_id | UUID | FK → subtasks |
| completed_date | DATE | 완료 날짜 |
| completed_at | TIMESTAMP | |

### one_time_completions (일회성 퀘스트 완료 기록)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID | PK |
| subtask_id | UUID | FK → subtasks |
| completed_at | TIMESTAMP | |

### intimacy_logs
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID | PK |
| npc_id | UUID | FK → npcs (NULL이면 self) |
| delta | INT | 변화량 (+/-) |
| reason | TEXT | 퀘스트 완료 등 이유 |
| created_at | TIMESTAMP | |

---

## 5. 핵심 로직

### 퀘스트 완료 조건
- 퀘스트의 **모든 서브태스크**가 완료되어야 퀘스트 완료 처리
- daily 퀘스트: 날짜 기준으로 완료 여부 판단 (매일 리셋)
- one-time 퀘스트: 한 번 완료되면 archived 처리

### 오늘의 미션 산출
- daily 퀘스트 중 routine 설정이 오늘 날짜에 해당하는 것만 표시
- daily_completions에 오늘 날짜 레코드가 없는 서브태스크 = 미완료

### 행복 레벨 계산
```
self_intimacy  = SUM(intimacy_logs.delta) WHERE npc_id IS NULL
others_total   = 각 NPC별 SUM(delta)의 합산

happiness_score = (self_intimacy × 0.4) + (others_total_avg × 0.6)
happiness_level = floor(happiness_score / 100) + 1  → lv.1, lv.2, lv.3 ...
```
- 친밀도는 상한 없이 무한 누적 (클리핑 없음)
- 행복은 "확률(%)" 아닌 "레벨(lv.N)"로 표시
- 레벨이 오를수록 픽셀 블록이 채워지고 다음 레벨 임계값까지의 진행도 표시
- "나를 사랑하기" 퀘스트 완료 시 npc_id=NULL로 intimacy_logs 기록

---

## 6. UI 구성

### 비주얼 스타일
- 배경: `#0d1117` (다크 네이비)
- 포인트 컬러: `#e94560` (레트로 레드)
- 보조 컬러: `#a8dadc`, `#ffd32a`
- 폰트: `Courier New` (모노스페이스)
- 테마: 레트로 픽셀 RPG

### 화면 ① 메인 대시보드
- 오늘의 미션 현황 (daily 퀘스트 + 서브태스크)
- NPC 목록 + 친밀도 미리보기
- 행복 레벨 — **픽셀 블록 채우기** 방식 (레벨업 개념)
  ```
  ■ ■ ■ ■ ■ ■ □ □ □ □  lv.3 → lv.4 진행중
  ```

### 화면 ② 퀘스트 보드
- 상단 탭: [나 자신] [NPC1] [NPC2] ... [+ 추가]
- 탭 선택 시 해당 니즈 목록 표시
- 퀘스트 추가/편집/삭제

### 화면 ③ NPC 상세 (드릴다운 아코디언)
```
[NPC 캐릭터 + 이름 + 친밀도 바]

니즈 목록
├── ▶ 자주 연락받고 싶어함          ← 클릭하면 펼침
│   ├── ▶ 주 1회 전화하기 [weekly]  ← 클릭하면 서브태스크 펼침
│   │   ├── ☑ 안부 물어보기
│   │   └── ☐ 근황 공유하기
│   └── ▶ 생일 챙기기 [one-time]
│       └── ☐ 케이크 주문
└── ▶ 건강한 모습 보고싶어함
    └── ▶ 운동 습관 만들기 [daily]
        ├── ☐ 30분 산책
        └── ☐ 스트레칭 10분
```

---

## 7. NPC 캐릭터 생성

5줄 특수문자 아트. 등록 시 랜덤 생성, 재생성 가능.

```
줄 1 (머리 장식): ╭✿╮ / ∧∧∧ / ★ ─ ★ / ♡ ♡ ♡ / ◈ ✦ ◈
줄 2 (얼굴):      눈 ∈ {◉, ⊙, ★, ♥, ─, ˘, ω} + 입 ∈ {ω, ▽, ‿, 3, ▿}
줄 3 (상체):      ╰▽╯ / ─═══─ / ╔═══╗ / ╭───╮
줄 4 (몸):        /||\ / ╱   ╲ / ║   ║ / ╰───╯
줄 5 (발):        ◡ ◡ / ▔   ▔ / ╚═ ═╝ / ∪   ∪
색상: 등록 순서에 따라 팔레트에서 자동 배정 (겹치지 않음)
```

---

## 8. 텔레그램 봇

- **연결 방식**: Webhook (polling 대신 — 서버 자원 절약)
- **브리핑 시간**: 설정 가능 (APScheduler 사용)

### 브리핑 포맷
```
🎮 LOVE QUEST — 오늘의 브리핑

[ 나를 사랑하기 ]
◆ 아침 루틴 (2/3)
  ☑ 기상 후 물 한잔
  ☑ 명상 10분
  ☐ 일기 쓰기  [완료]

[ 타인을 사랑하기 ]
◆ 엄마 — 주 1회 전화하기
  ☐ 안부 물어보기  [완료]
  ☐ 근황 공유하기  [완료]

행복 레벨: ■■■■■■□□□□ lv.3 → lv.4
```

- 각 서브태스크 옆 `[완료]` = 인라인 버튼
- 버튼 누르면 완료 처리 + 메시지 업데이트

### 봇 명령어
| 명령어 | 기능 |
|---|---|
| /brief | 즉시 브리핑 |
| /quests | 전체 퀘스트 목록 |
| /status | 행복 레벨 + NPC 친밀도 현황 |

---

## 9. 레벨업 보상

레벨이 오를 때마다 사전에 설정해둔 나 자신을 위한 보상 메시지가 표시된다.

### level_rewards 테이블
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID | PK |
| level | INT | 보상이 발동하는 레벨 (1, 2, 3...) |
| message | TEXT | 보상 내용 (예: "맛있는 거 사먹기", "영화 보기") |
| is_claimed | BOOL | 보상 수령 여부 |
| claimed_at | TIMESTAMP | 수령 시각 |

### 동작 방식
- 웹: 레벨업 시 팝업으로 보상 메시지 표시 + "보상 받기" 버튼
- 텔레그램: 레벨업 이벤트 발생 시 즉시 메시지 전송
  ```
  🎉 LEVEL UP! lv.3 → lv.4
  
  ✨ 나에게 주는 선물:
  "좋아하는 카페에서 케이크 먹기"
  
  [보상 받기]
  ```
- 보상을 미리 설정하지 않은 레벨은 기본 축하 메시지만 표시
- 보상은 웹에서 레벨별로 미리 작성해둘 수 있음

---

## 10. 미포함 범위 (v1)

- 사용자 인증 (단일 사용자 앱, 인증 없음)
- 푸시 알림 (텔레그램 브리핑으로 대체)
- 퀘스트 통계/히스토리 상세 차트
- 모바일 앱 (웹 반응형으로 대체)
