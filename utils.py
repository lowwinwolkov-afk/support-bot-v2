from datetime import datetime, timedelta

def now():
    return datetime.now()

def fmt():
    return now().strftime("%Y-%m-%d %H:%M:%S")

def add_hours(h):
    return (now() + timedelta(hours=h)).strftime("%Y-%m-%d %H:%M:%S")

def add_days(d):
    return (now() + timedelta(days=d)).strftime("%Y-%m-%d %H:%M:%S")
