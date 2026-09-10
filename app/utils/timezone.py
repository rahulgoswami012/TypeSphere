from datetime import datetime, timezone, timedelta, date
from typing import Tuple

# Indian Standard Time: UTC+05:30
IST_OFFSET = timedelta(hours=5, minutes=30)
IST = timezone(IST_OFFSET, name="IST")

def now_ist() -> datetime:
    """Returns current aware datetime in Indian Standard Time."""
    return datetime.now(timezone.utc).astimezone(IST)

def now_utc() -> datetime:
    """Returns current naive UTC timestamp for standard DB storage."""
    return datetime.utcnow()

def to_ist(dt: datetime) -> datetime:
    """Converts a naive or aware UTC datetime to IST."""
    if dt is None:
        return now_ist()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)

def ist_today() -> date:
    """Returns the current calendar date in IST."""
    return now_ist().date()

def ist_today_bounds() -> Tuple[datetime, datetime]:
    """
    Returns naive UTC datetime bounds (start, end) representing 
    00:00:00 to 23:59:59.999999 of the current IST calendar day.
    Used for strict SQL date-window queries.
    """
    current_ist = now_ist()
    start_ist = datetime(current_ist.year, current_ist.month, current_ist.day, 0, 0, 0, tzinfo=IST)
    end_ist = start_ist + timedelta(days=1)
    
    start_utc = start_ist.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_ist.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc

def get_ist_hour(dt: datetime = None) -> int:
    """Returns the hour (0-23) in IST for night owl/early bird calculations."""
    target = to_ist(dt) if dt else now_ist()
    return target.hour