from datetime import datetime, timezone

from pipeline.stages.sending import daily_limit, in_send_window


def test_send_window_weekdays_only():
    assert in_send_window(datetime(2026, 11, 4, 9, 0, tzinfo=timezone.utc))  # Wed 10:00 Berlin
    assert not in_send_window(datetime(2026, 11, 7, 9, 0, tzinfo=timezone.utc))  # Sat
    assert not in_send_window(datetime(2026, 11, 4, 17, 30, tzinfo=timezone.utc))  # 18:30 Berlin
    assert not in_send_window(datetime(2026, 11, 4, 6, 30, tzinfo=timezone.utc))  # 07:30 Berlin


def test_daily_limit_ramp():
    first = datetime(2026, 1, 5, tzinfo=timezone.utc)
    assert daily_limit(None) == 30
    assert daily_limit(first, datetime(2026, 1, 6, tzinfo=timezone.utc)) == 30
    assert daily_limit(first, datetime(2026, 1, 13, tzinfo=timezone.utc)) == 50
    assert daily_limit(first, datetime(2026, 12, 1, tzinfo=timezone.utc)) == 150
