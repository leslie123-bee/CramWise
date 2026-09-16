import re
from datetime import datetime

VALID_DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
VALID_DIFFICULTIES = ['easy', 'medium', 'hard']
VALID_PERIODS = ['morning', 'afternoon', 'evening']

_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
# Deliberately simple (not the full RFC 5322 grammar) - just enough to
# catch "not an email at all" typos without rejecting real addresses.
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

# Generous ceilings on free-text fields - not about being strict, just
# stopping someone (or a bug) from writing megabytes of text into a
# single row. None of these should ever be hit by normal use.
MAX_LENGTHS = {
    'name': 100,
    'email': 254,
    'password': 256,
    'subject_name': 100,
    'exam_name': 150,
    'topic': 150,
    'group_name': 100,
    'school_name': 150,
    'announcement_title': 150,
    'announcement_body': 4000,
    'tutor_message': 4000,
    'study_goal': 300,
}


def is_non_empty_string(v):
    return isinstance(v, str) and v.strip() != ''


def is_valid_email(v):
    return isinstance(v, str) and len(v) <= MAX_LENGTHS['email'] and bool(_EMAIL_RE.match(v.strip()))


def within_max_length(v, field):
    """True if v is a string within MAX_LENGTHS[field] (or v is falsy -
    an optional field left blank is not this check's problem)."""
    if not v:
        return True
    return isinstance(v, str) and len(v) <= MAX_LENGTHS[field]


def is_valid_date(v):
    if not isinstance(v, str) or not _DATE_RE.match(v):
        return False
    try:
        datetime.strptime(v, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def is_valid_difficulty(v):
    return v in VALID_DIFFICULTIES


def is_valid_period(v):
    return v in VALID_PERIODS


def is_valid_days_array(v):
    return isinstance(v, list) and len(v) > 0 and all(d in VALID_DAYS for d in v)
