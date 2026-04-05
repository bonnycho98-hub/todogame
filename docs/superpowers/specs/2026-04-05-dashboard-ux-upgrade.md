# Dashboard UX Upgrade — Design Spec

## Goal

대시보드를 게임 플레이어가 현재 상황을 한눈에 파악할 수 있도록 개선한다. 진행 중인 퀘스트를 바로 보여주고, NPC들의 니즈를 캐릭터 말투로 표시하며, 니즈 완료 처리를 지원한다. 기존 레트로 도트 게임 스타일(Courier New, 다크 배경, 빨간 강조)은 그대로 유지한다.

## Architecture

기존 SPA(단일 HTML + app.js) 구조를 그대로 따른다. 백엔드는 FastAPI + SQLAlchemy. 대시보드 API(`GET /api/dashboard`)를 확장해 NPC별 활성 니즈를 함께 반환하도록 한다. 니즈 완료는 새 엔드포인트(`POST /api/needs/{id}/complete`)로 처리한다.

## Tech Stack

FastAPI, SQLAlchemy, Pydantic v1, Alembic, Vanilla JS (SPA), Courier New 폰트 기반 레트로 CSS

---

## 1. 백엔드: Need 완료 처리

### 1-1. 모델 변경

`Need` 모델에 `is_archived` 컬럼 추가:

```python
is_archived = Column(Boolean, default=False)
```

### 1-2. Alembic 마이그레이션

새 컬럼을 추가하는 마이그레이션 파일 생성:

```python
op.add_column('needs', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'))
```

### 1-3. 니즈 완료 엔드포인트

`POST /api/needs/{need_id}/complete`

- `need.is_archived = True` 로 설정
- 친밀도 보상 없음
- 반환: `{"done": true}`

### 1-4. list_needs 필터링

`GET /api/needs` 에서 기본적으로 `is_archived=False` 인 것만 반환.

---

## 2. 백엔드: 대시보드 API 확장

### 2-1. NPCSummary 스키마 확장

```python
class NPCSummary(BaseModel):
    id: UUID
    name: str
    sprite: str
    color: str
    intimacy_total: int
    needs: list[NeedOut]  # 활성 니즈 목록 추가
```

### 2-2. 대시보드 라우터 변경

`GET /api/dashboard` 응답에서 각 NPC의 활성(is_archived=False) 니즈를 포함해서 반환.

---

## 3. 백엔드: 행복 레벨 난이도 하향

`app/services/happiness.py`:

```python
POINTS_PER_LEVEL = 30  # 기존 100 → 30
```

---

## 4. 프론트엔드: 대시보드 퀘스트 섹션

### 4-1. 퀘스트 목록 렌더링

대시보드의 `▸ ACTIVE QUESTS` 섹션에 `today_quests` 목록을 렌더링한다.

각 아이템:
```
[진행률]  퀘스트 제목          DAILY/QUEST  ›
```
- 진행률: `완료된 서브태스크 수 / 전체 서브태스크 수` → `[1/3]`
- 서브태스크가 없는 퀘스트는 `[–]` 표시
- 진행 중(1개 이상 완료)인 퀘스트는 `border: 1px solid var(--red)` 강조
- 클릭 시 퀘스트 모달 오픈

### 4-2. 퀘스트 모달

기존 `.modal` / `.modal-overlay` CSS 클래스 재사용.

모달 내용:
- 헤더: 퀘스트 타입(DAILY/QUEST), 퀘스트 제목
- 서브태스크 목록: 체크박스 + 제목 (완료된 것은 취소선)
- 각 체크박스 클릭 → `POST /api/subtasks/{id}/complete` 호출
- `[ 퀘스트 전체 완료 ]` 버튼 → `POST /api/quests/{id}/complete` 호출
- 레벨업 시 기존 레벨업 팝업 표시
- 완료 후 모달 닫고 대시보드 새로고침

---

## 5. 프론트엔드: NPC 카드 (대시보드)

### 5-1. NPC 카드 레이아웃

기존 대시보드 NPC 섹션을 교체. `▸ CHARACTERS` 섹션으로 변경.

각 NPC 카드:
```
[ASCII 스프라이트]  NPC이름          ♥ 240
                  ▷ "니즈 내용..."   [완료]
                  ▷ "니즈 내용..."   [완료]
```

- ASCII 스프라이트: 기존 `sprite` JSON 렌더링 함수 재사용
- 니즈가 없으면 `— 니즈 없음 —` 표시
- `완료` 버튼: `POST /api/needs/{id}/complete` 호출 후 대시보드 새로고침

### 5-2. 스타일

기존 CSS 변수 사용:
- NPC 이름: `color: var(--yellow)`
- 니즈 텍스트: `color: var(--text)`
- `▷` 화살표: `color: var(--muted)`
- 완료 버튼: `border: 1px solid var(--green); color: var(--green)`

---

## 6. 변경 범위 요약

| 파일 | 변경 유형 |
|------|----------|
| `app/models.py` | Need에 `is_archived` 추가 |
| `alembic/versions/새파일.py` | needs 테이블에 컬럼 추가 마이그레이션 |
| `app/schemas.py` | NPCSummary에 `needs` 필드 추가, NeedComplete 응답 스키마 추가 |
| `app/routers/needs.py` | `POST /{need_id}/complete` 엔드포인트 추가, list_needs 필터링 |
| `app/routers/dashboard.py` | NPC 조회 시 needs 포함 |
| `app/services/happiness.py` | POINTS_PER_LEVEL 100 → 30 |
| `static/app.js` | 대시보드 렌더링 함수 전면 수정 |

---

## 7. 범위 외 (이번 스펙에 포함 안 됨)

- 텔레그램 AI 연동 (Sub-project B)
- 니즈 완료 시 친밀도 보상
- NPC 카드에서 퀘스트 바로 추가
