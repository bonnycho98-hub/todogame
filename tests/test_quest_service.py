from datetime import date
from app.services.quest import is_routine_match


def test_daily_routine_always_active():
    assert is_routine_match({"type": "daily"}, date(2026, 4, 5)) is True


def test_weekly_routine_matches_correct_day():
    # 2026-04-06 = 월요일 (weekday=0)
    assert is_routine_match({"type": "weekly", "days": [0]}, date(2026, 4, 6)) is True


def test_weekly_routine_skips_wrong_day():
    # 2026-04-06 = 월요일, 화(1) 목(3)은 아님
    assert is_routine_match({"type": "weekly", "days": [1, 3]}, date(2026, 4, 6)) is False


def test_monthly_routine_matches_correct_date():
    assert is_routine_match({"type": "monthly", "dates": [5, 15]}, date(2026, 4, 5)) is True


def test_monthly_routine_skips_wrong_date():
    assert is_routine_match({"type": "monthly", "dates": [1, 15]}, date(2026, 4, 5)) is False


def test_none_routine_not_active():
    assert is_routine_match(None, date.today()) is False
