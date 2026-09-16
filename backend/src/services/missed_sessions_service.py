# Flips any session whose date+time has passed while still 'not_started'
# into 'missed'. Called lazily on relevant GET requests and swept
# periodically from server.py - see that file for the interval.
from datetime import datetime

from ..config.db import db


def mark_missed_sessions():
    now = datetime.now()
    now_date = now.strftime('%Y-%m-%d')
    now_time = now.strftime('%H:%M')

    result = db.run(
        '''UPDATE sessions
           SET status = 'missed'
           WHERE status = 'not_started'
             AND (session_date < ? OR (session_date = ? AND start_time < ?))''',
        (now_date, now_date, now_time),
    )
    return result['changes']
