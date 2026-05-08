from datetime import datetime, timedelta

# ---------------- ВРЕМЯ ----------------
def now():
    return datetime.now()

def now_str():
    return now().strftime("%Y-%m-%d %H:%M:%S")

def add_hours(hours):
    return (now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")

def add_days(days):
    return (now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

# ---------------- ФОРМАТИРОВАНИЕ ----------------
def ticket_title(ticket_id, username, status="🆕"):
    return f"{status} [#{ticket_id}] {username}"

def log_text(event, ticket_id, support=None, old=None):
    text = (
        f"📋 СОБЫТИЕ: {event}\n"
        f"🎫 ТИКЕТ: #{ticket_id}\n"
    )

    if support:
        text += f"👨‍💻 ОТВЕТСТВЕННЫЙ: {support}\n"

    if old:
        text += f"🔄 ПРЕДЫДУЩИЙ: {old}\n"

    text += f"⏰ ВРЕМЯ: {now_str()}"

    return text

# ---------------- ПРИОРИТЕТЫ ----------------
HIGH_PRIORITY_WORDS = [
    "срочно",
    "авария",
    "не работает",
    "ошибка оплаты",
    "сломалось",
    "critical",
    "urgent",
    "побыстрее",
    "быстрее",
    "взломали"
]

def detect_priority(text):
    text = text.lower()

    for word in HIGH_PRIORITY_WORDS:
        if word in text:
            return "🔥 HIGH"

    return "ℹ️ NORMAL"

# ---------------- СТАТУСЫ ----------------
STATUS_EMOJIS = {
    "NEW": "🆕",
    "IN_PROGRESS": "🟢",
    "WAITING": "🟡",
    "CLOSED": "🔴"
}

def status_emoji(status):
    return STATUS_EMOJIS.get(status, "ℹ️")

# ---------------- MARKDOWN ----------------
def escape_md(text):
    chars = r"_*[]()~`>#+-=|{}.!"
    for ch in chars:
        text = text.replace(ch, f"\\{ch}")
    return text

# ---------------- SLA ----------------
def minutes_passed(created_at):
    created = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    delta = now() - created
    return int(delta.total_seconds() / 60)

def sla_badge(created_at):
    mins = minutes_passed(created_at)

    if mins >= 30:
        return f"🔴 {mins} мин"

    elif mins >= 15:
        return f"🟡 {mins} мин"

    return f"🟢 {mins} мин"

# ---------------- ТЕГИ ----------------
TAGS = {
    "payment": "💸 Оплата",
    "bug": "🐛 Баг",
    "idea": "📢 Предложение",
    "account": "👤 Аккаунт"
}

def get_tag(tag_key):
    return TAGS.get(tag_key, "🏷 Без тега")

# ---------------- БЕЙДЖИ ----------------
def waiting_badge():
    return "⌛ Ожидает ответа"

def closed_badge():
    return "✅ Закрыт"

# ---------------- ШАБЛОНЫ ----------------
DEFAULT_TEMPLATES = {
    "hello": "Здравствуйте! Спасибо за обращение.",
    "wait": "Пожалуйста, ожидайте. Мы проверяем информацию.",
    "close": "Ваш тикет был успешно закрыт."
}

def get_template(name):
    return DEFAULT_TEMPLATES.get(name)
