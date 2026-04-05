from app.services.happiness import calculate_happiness, POINTS_PER_LEVEL


def test_zero_intimacy_is_level_1():
    result = calculate_happiness(self_total=0, others_totals=[])
    assert result["level"] == 1
    assert result["progress"] == 0


def test_level_increases_with_score():
    # POINTS_PER_LEVEL만큼 score → lv.2
    total = POINTS_PER_LEVEL
    result = calculate_happiness(self_total=total, others_totals=[total])
    assert result["level"] == 2


def test_progress_within_level():
    # 레벨의 절반 → progress=0.5
    half = POINTS_PER_LEVEL // 2
    result = calculate_happiness(self_total=half, others_totals=[half])
    assert result["level"] == 1
    assert abs(result["progress"] - 0.5) < 0.01


def test_others_avg_used_not_sum():
    # 두 NPC 각각 같은 값 → others_avg 동일 → 레벨 동일
    total = POINTS_PER_LEVEL
    result_one = calculate_happiness(self_total=total, others_totals=[total])
    result_two = calculate_happiness(self_total=total, others_totals=[total, total])
    assert result_one["level"] == result_two["level"]


def test_pixel_blocks():
    # 레벨의 60% → 6 블록
    pts = int(POINTS_PER_LEVEL * 0.6)
    result = calculate_happiness(self_total=pts, others_totals=[pts])
    assert result["filled_blocks"] == 6
    assert result["total_blocks"] == 10
