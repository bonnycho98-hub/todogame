from app.services.happiness import calculate_happiness, POINTS_PER_LEVEL


def test_zero_intimacy_is_level_1():
    result = calculate_happiness(self_total=0, others_totals=[])
    assert result["level"] == 1
    assert result["progress"] == 0


def test_level_increases_with_score():
    # score = 100*0.4 + 100*0.6 = 100 → lv.2
    result = calculate_happiness(self_total=100, others_totals=[100])
    assert result["level"] == 2


def test_progress_within_level():
    # score = 50*0.4 + 50*0.6 = 50 → lv.1, progress = 0.5
    result = calculate_happiness(self_total=50, others_totals=[50])
    assert result["level"] == 1
    assert abs(result["progress"] - 0.5) < 0.01


def test_others_avg_used_not_sum():
    # 두 NPC 각각 100 → others_avg=100, self=100 → score=100 → lv.2
    result_one = calculate_happiness(self_total=100, others_totals=[100])
    result_two = calculate_happiness(self_total=100, others_totals=[100, 100])
    assert result_one["level"] == result_two["level"]


def test_pixel_blocks():
    # score = 60*0.4 + 60*0.6 = 60 → progress=0.6 → 6 blocks
    result = calculate_happiness(self_total=60, others_totals=[60])
    assert result["filled_blocks"] == 6
    assert result["total_blocks"] == 10
