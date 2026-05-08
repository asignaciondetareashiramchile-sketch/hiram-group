import datetime
import pytz
from backend.config import CHILE_HOLIDAYS

CHILE_TZ = pytz.timezone("America/Santiago")
BUSINESS_START = 9   # 09:00
BUSINESS_END = 18    # 18:00


def now_chile():
    return datetime.datetime.now(CHILE_TZ)


def is_business_day(dt):
    if dt.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    date_str = dt.strftime("%Y-%m-%d")
    return date_str not in CHILE_HOLIDAYS


def next_business_day(dt):
    dt = dt + datetime.timedelta(days=1)
    while not is_business_day(dt):
        dt = dt + datetime.timedelta(days=1)
    return dt


def add_business_hours(start_dt, hours):
    """Add business hours to a datetime, respecting business hours 09:00-18:00."""
    dt = start_dt
    if isinstance(dt, datetime.datetime) and dt.tzinfo is None:
        dt = CHILE_TZ.localize(dt)

    remaining = hours
    while remaining > 0:
        if not is_business_day(dt):
            dt = next_business_day(dt).replace(hour=BUSINESS_START, minute=0, second=0)
            continue
        if dt.hour >= BUSINESS_END:
            dt = next_business_day(dt).replace(hour=BUSINESS_START, minute=0, second=0)
            continue
        if dt.hour < BUSINESS_START:
            dt = dt.replace(hour=BUSINESS_START, minute=0, second=0)

        hours_until_end = BUSINESS_END - dt.hour - (dt.minute / 60)
        if remaining <= hours_until_end:
            dt = dt + datetime.timedelta(hours=remaining)
            remaining = 0
        else:
            remaining -= hours_until_end
            dt = next_business_day(dt).replace(hour=BUSINESS_START, minute=0, second=0)

    return dt


def add_business_days(start_dt, days):
    """Add business days to a datetime."""
    dt = start_dt
    if isinstance(dt, datetime.datetime) and dt.tzinfo is None:
        dt = CHILE_TZ.localize(dt)

    count = 0
    while count < days:
        dt = dt + datetime.timedelta(days=1)
        if is_business_day(dt):
            count += 1
    return dt.replace(hour=BUSINESS_END, minute=0, second=0)


def calculate_deadline(priority):
    from backend.models import PriorityEnum, PRIORITY_CONFIG
    now = now_chile()
    cfg = PRIORITY_CONFIG[priority]

    if priority == PriorityEnum.URGENT:
        return add_business_hours(now, cfg["hours"])
    elif priority == PriorityEnum.HIGH:
        # Same business day at 18:00
        if is_business_day(now) and now.hour < BUSINESS_END:
            return now.replace(hour=BUSINESS_END, minute=0, second=0)
        else:
            nd = next_business_day(now)
            return nd.replace(hour=BUSINESS_END, minute=0, second=0)
    else:
        return add_business_days(now, cfg["days"])


def format_deadline(dt):
    if dt is None:
        return "Sin fecha"
    if dt.tzinfo is None:
        dt = CHILE_TZ.localize(dt)
    return dt.strftime("%d/%m/%Y %H:%M")


def is_overdue(deadline):
    if deadline is None:
        return False
    now = now_chile()
    if deadline.tzinfo is None:
        deadline = CHILE_TZ.localize(deadline)
    return now > deadline
