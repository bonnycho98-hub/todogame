import math

POINTS_PER_LEVEL = 100


def calculate_happiness(self_total: int, others_totals: list) -> dict:
    """
    self_total: 나 자신 친밀도 누적 합계
    others_totals: 각 NPC 친밀도 누적 합계 리스트

    반환:
      level        : 현재 행복 레벨 (1부터 시작)
      score        : 현재 행복 점수 (소수점 가능)
      progress     : 현재 레벨 내 진행도 0.0 ~ 1.0
      filled_blocks: 채워진 픽셀 블록 수 (0~10)
      total_blocks : 10
    """
    others_avg = sum(others_totals) / len(others_totals) if others_totals else 0
    score = (self_total * 0.4) + (others_avg * 0.6)

    level = math.floor(score / POINTS_PER_LEVEL) + 1
    progress_score = score % POINTS_PER_LEVEL
    progress = progress_score / POINTS_PER_LEVEL

    total_blocks = 10
    filled_blocks = math.floor(progress * total_blocks)

    return {
        "level": level,
        "score": round(score, 1),
        "progress": round(progress, 3),
        "filled_blocks": filled_blocks,
        "total_blocks": total_blocks,
    }
