from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))


def today_kst():
    return datetime.now(KST).date()
