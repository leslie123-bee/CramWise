# Generates (or regenerates) a study timetable for a user, following the
# rules described in the blueprint's "How the Smart Planner should decide"
# section:
#   1. Weight each subject by how soon its exam is and how hard it is.
#   2. Open the available slots between tomorrow and the furthest exam.
#   3. Fill slots in weighted rotation so nothing gets dropped.
#   4. Default every session to a fixed block (60 min).
#   5. Never touch sessions the student already started/completed/edited
#      into the past - only future 'not_started' sessions are replaced.
import json
import uuid
from datetime import date, timedelta

from ..config.db import db
from ..lib.http_kit import HttpError

DAY_NAMES = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']  # date.weekday(): Mon=0 .. Sun=6
DIFFICULTY_SCORE = {'easy': 1, 'medium': 2, 'hard': 3}
PERIOD_START = {'morning': '08:00', 'afternoon': '14:00', 'evening': '19:00'}
SLOTS_PER_DAY = 2
SLOT_DURATION_MINUTES = 60
GAP_MINUTES = 15
DEFAULT_WINDOW_DAYS = 14  # used when the student has no exams yet


def _day_name(d):
    return DAY_NAMES[d.weekday()]


def generate_timetable(user_id):
    user = db.get('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if not user:
        raise HttpError(404, 'User not found')

    subjects = db.all('SELECT * FROM subjects WHERE user_id = ?', (user_id,))
    if not subjects:
        raise HttpError(400, 'Add at least one subject before generating a plan')

    available_days = json.loads(user.get('available_days') or '[]')
    if not available_days:
        raise HttpError(400, 'Set your available study days (in your profile) before generating a plan')

    exams = db.all('SELECT * FROM exams WHERE user_id = ?', (user_id,))
    today = date.today()

    # 1. Plan window: up to the furthest exam, or a default window if none yet.
    if exams:
        window_end = date.fromisoformat(max(e['exam_date'] for e in exams))
    else:
        window_end = today + timedelta(days=DEFAULT_WINDOW_DAYS)

    # 2. Candidate study dates: tomorrow through the window end, on available days only.
    dates = []
    d = today + timedelta(days=1)
    while d <= window_end:
        if _day_name(d) in available_days:
            dates.append(d)
        d += timedelta(days=1)
    if not dates:
        raise HttpError(400, 'None of your available study days fall before your next exam')

    # 3. Weight each subject.
    weighted = []
    for subject in subjects:
        subject_exams = [e for e in exams if e['subject_id'] == subject['subject_id']]
        nearest_exam_date = None
        exam_score = 2  # baseline so subjects without an exam yet still get scheduled
        if subject_exams:
            nearest_exam_date = min(e['exam_date'] for e in subject_exams)
            days_until = max(1, (date.fromisoformat(nearest_exam_date) - today).days)
            exam_score = max(3, round(90 / days_until))  # closer exam -> bigger score
        difficulty_score = DIFFICULTY_SCORE.get(subject['difficulty'], 2)
        weighted.append({'subject': subject, 'nearest_exam_date': nearest_exam_date, 'weight': exam_score + difficulty_score})

    # 4. Build slots (chronological) and assign subjects via smooth weighted round robin,
    #    which spreads high-weight subjects evenly instead of clumping them up front.
    total_slots = len(dates) * SLOTS_PER_DAY
    order = _smooth_weighted_round_robin(
        [{'id': w['subject']['subject_id'], 'weight': w['weight']} for w in weighted],
        total_slots,
    )

    start_time = PERIOD_START.get(user.get('preferred_study_time'), '18:00')
    slots = []
    for d in dates:
        date_str = d.isoformat()
        for i in range(SLOTS_PER_DAY):
            slots.append({'date': date_str, 'start_time': _add_minutes_to_time(start_time, i * (SLOT_DURATION_MINUTES + GAP_MINUTES))})
    assignments = [{**slot, 'subject_id': order[i]} for i, slot in enumerate(slots)]

    # 5. Guarantee: every subject with an exam gets at least one session before it.
    for w in weighted:
        if not w['nearest_exam_date']:
            continue
        covered = any(a['subject_id'] == w['subject']['subject_id'] and a['date'] < w['nearest_exam_date'] for a in assignments)
        if not covered:
            for a in assignments:
                if a['date'] < w['nearest_exam_date']:
                    a['subject_id'] = w['subject']['subject_id']
                    break

    # 6. Replace future not-started sessions only - past history and anything
    #    the student has started, completed, or hand-edited is left alone.
    from_date = (today + timedelta(days=1)).isoformat()

    # The delete + inserts + commit all happen while holding db.lock, so a
    # request from another user (now possible at the same time, since the
    # server handles requests on multiple threads) can't run a write in
    # between and end up interleaved with this transaction.
    conn = db.connection
    with db.lock:
        conn.execute("DELETE FROM sessions WHERE user_id = ? AND status = 'not_started' AND session_date >= ?", (user_id, from_date))
        conn.execute('BEGIN')
        try:
            for a in assignments:
                conn.execute(
                    '''INSERT INTO sessions (session_id, user_id, subject_id, topic, session_date, start_time, duration_minutes)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (str(uuid.uuid4()), user_id, a['subject_id'], 'General review', a['date'], a['start_time'], SLOT_DURATION_MINUTES),
                )
            conn.execute('COMMIT')
        except Exception:
            conn.execute('ROLLBACK')
            raise

    return db.all('SELECT * FROM sessions WHERE user_id = ? AND session_date >= ? ORDER BY session_date, start_time', (user_id, from_date))


def _smooth_weighted_round_robin(items, n):
    # Same idea nginx uses for weighted load balancing - spreads
    # higher-weight items evenly across the output instead of clustering
    # them at the start.
    state = [{'id': it['id'], 'weight': it['weight'], 'current': 0} for it in items]
    total = sum(it['weight'] for it in state)
    result = []
    for _ in range(n):
        for it in state:
            it['current'] += it['weight']
        best = max(state, key=lambda it: it['current'])
        result.append(best['id'])
        best['current'] -= total
    return result


def _add_minutes_to_time(hhmm, minutes):
    h, m = (int(x) for x in hhmm.split(':'))
    total = h * 60 + m + minutes
    return f'{(total % 1440) // 60:02d}:{total % 60:02d}'
