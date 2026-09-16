# Computes everything the Progress screen shows, per the blueprint:
# study time (today/week/month), completed vs planned sessions,
# per-subject progress %, study streak, goal progress, and the
# subjects that need attention.
from datetime import date, timedelta

from ..config.db import db


def get_progress(user_id):
    sessions = db.all('SELECT * FROM sessions WHERE user_id = ?', (user_id,))
    subjects = db.all('SELECT * FROM subjects WHERE user_id = ?', (user_id,))

    today = date.today()
    today_str = today.isoformat()
    week_start = (today - timedelta(days=6)).isoformat()   # today + 6 previous days = 7-day window
    month_start = (today - timedelta(days=29)).isoformat()  # today + 29 previous days = 30-day window

    completed = [s for s in sessions if s['status'] == 'completed']

    study_time = {
        'today': _sum_duration([s for s in completed if s['session_date'] == today_str]),
        'week': _sum_duration([s for s in completed if s['session_date'] >= week_start]),
        'month': _sum_duration([s for s in completed if s['session_date'] >= month_start]),
    }

    session_counts = {
        'completed': len(completed),
        'planned': len(sessions),
        'missed': len([s for s in sessions if s['status'] == 'missed']),
    }

    subject_progress = []
    for subject in subjects:
        subject_sessions = [s for s in sessions if s['subject_id'] == subject['subject_id']]
        subject_completed = len([s for s in subject_sessions if s['status'] == 'completed'])
        percent = round((subject_completed / len(subject_sessions)) * 100) if subject_sessions else 0
        subject_progress.append({
            'subject_id': subject['subject_id'],
            'subject_name': subject['subject_name'],
            'difficulty': subject['difficulty'],
            'completed': subject_completed,
            'planned': len(subject_sessions),
            'percent': percent,
        })

    # Streak: consecutive calendar days, walking back from today, with >=1 completed session.
    streak = _calculate_streak([s['session_date'] for s in completed])

    # Subjects needing attention: below 50% completion, worst first.
    needs_attention = sorted(
        (s for s in subject_progress if s['planned'] > 0 and s['percent'] < 50),
        key=lambda s: s['percent'],
    )[:5]

    goal_progress = round((session_counts['completed'] / len(sessions)) * 100) if sessions else 0

    return {
        'studyTime': study_time,
        'sessions': session_counts,
        'subjectProgress': subject_progress,
        'streak': streak,
        'goalProgress': goal_progress,
        'needsAttention': needs_attention,
    }


def _sum_duration(session_list):
    total = 0
    for s in session_list:
        actual = s.get('actual_duration_minutes')
        total += actual if actual is not None else (s.get('duration_minutes') or 0)
    return total


def _calculate_streak(dates_list):
    unique_dates = set(dates_list)
    streak = 0
    cursor = date.today()
    while cursor.isoformat() in unique_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
