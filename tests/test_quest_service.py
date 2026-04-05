from datetime import date
from unittest.mock import MagicMock
from app.services.quest import is_routine_match, is_quest_all_done_today
from app import models


def _make_subtask(done: bool) -> models.Subtask:
    st = MagicMock(spec=models.Subtask)
    st.id = "test-id"
    st.quest = MagicMock()
    st.quest.quest_type = models.QuestType.DAILY
    st.one_time_completion = None
    return st


def test_all_done_when_all_subtasks_done():
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = object()  # truthy

    quest = MagicMock(spec=models.Quest)
    quest.quest_type = models.QuestType.DAILY
    quest.subtasks = [_make_subtask(True), _make_subtask(True)]

    assert is_quest_all_done_today(db, quest, date(2026, 4, 5)) is True


def test_not_all_done_when_any_subtask_undone():
    db = MagicMock()
    # 첫 번째 subtask: 완료됨, 두 번째: 미완료
    db.query.return_value.filter_by.return_value.first.side_effect = [object(), None]

    quest = MagicMock(spec=models.Quest)
    quest.quest_type = models.QuestType.DAILY
    quest.subtasks = [_make_subtask(True), _make_subtask(False)]

    assert is_quest_all_done_today(db, quest, date(2026, 4, 5)) is False


def test_not_all_done_when_no_subtasks():
    db = MagicMock()
    quest = MagicMock(spec=models.Quest)
    quest.quest_type = models.QuestType.DAILY
    quest.subtasks = []

    assert is_quest_all_done_today(db, quest, date(2026, 4, 5)) is False


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
