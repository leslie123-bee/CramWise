import uuid

from ..config.db import db
from ..services.missed_sessions_service import mark_missed_sessions
from ..services.planner_service import generate_timetable
from ..utils.validators import is_non_empty_string, is_valid_date


def list_sessions(req, res, next_):
    mark_missed_sessions()

    query = 'SELECT * FROM sessions WHERE user_id = ?'
    params = [req.user_id]
    if req.query.get('from'):
        query += ' AND session_date >= ?'
        params.append(req.query['from'])
    if req.query.get('to'):
        query += ' AND session_date <= ?'
        params.append(req.query['to'])
    if req.query.get('status'):
        query += ' AND status = ?'
        params.append(req.query['status'])
    query += ' ORDER BY session_date, start_time'

    res.json(db.all(query, tuple(params)))


def get_one(req, res, next_):
    session = db.get('SELECT * FROM sessions WHERE session_id = ? AND user_id = ?', (req.params['id'], req.user_id))
    if not session:
        return res.status(404).json({'error': 'Session not found'})
    res.json(session)


def create_session(req, res, next_):
    body = req.body or {}
    subject_id = body.get('subject_id')
    topic = body.get('topic')
    session_date = body.get('session_date')
    start_time = body.get('start_time')
    duration_minutes = body.get('duration_minutes')

    if not is_non_empty_string(subject_id) or not is_valid_date(session_date) or not is_non_empty_string(start_time):
        return res.status(400).json({'error': 'subject_id, session_date (YYYY-MM-DD), and start_time (HH:MM) are required'})

    subject = db.get('SELECT * FROM subjects WHERE subject_id = ? AND user_id = ?', (subject_id, req.user_id))
    if not subject:
        return res.status(404).json({'error': 'Subject not found'})

    session_id = str(uuid.uuid4())
    db.run(
        '''INSERT INTO sessions (session_id, user_id, subject_id, topic, session_date, start_time, duration_minutes)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (session_id, req.user_id, subject_id, topic or 'General review', session_date, start_time, duration_minutes or 60),
    )
    res.status(201).json(db.get('SELECT * FROM sessions WHERE session_id = ?', (session_id,)))


def update_session(req, res, next_):
    session = db.get('SELECT * FROM sessions WHERE session_id = ? AND user_id = ?', (req.params['id'], req.user_id))
    if not session:
        return res.status(404).json({'error': 'Session not found'})

    body = req.body or {}
    subject_id = body.get('subject_id')
    topic = body.get('topic')
    session_date = body.get('session_date')
    start_time = body.get('start_time')
    duration_minutes = body.get('duration_minutes')

    if subject_id:
        subject = db.get('SELECT * FROM subjects WHERE subject_id = ? AND user_id = ?', (subject_id, req.user_id))
        if not subject:
            return res.status(404).json({'error': 'Subject not found'})
    if session_date is not None and not is_valid_date(session_date):
        return res.status(400).json({'error': 'session_date must be a valid date (YYYY-MM-DD)'})

    db.run(
        '''UPDATE sessions SET
             subject_id = COALESCE(?, subject_id),
             topic = COALESCE(?, topic),
             session_date = COALESCE(?, session_date),
             start_time = COALESCE(?, start_time),
             duration_minutes = COALESCE(?, duration_minutes)
           WHERE session_id = ?''',
        (subject_id, topic, session_date, start_time, duration_minutes, req.params['id']),
    )
    res.json(db.get('SELECT * FROM sessions WHERE session_id = ?', (req.params['id'],)))


def delete_session(req, res, next_):
    session = db.get('SELECT * FROM sessions WHERE session_id = ? AND user_id = ?', (req.params['id'], req.user_id))
    if not session:
        return res.status(404).json({'error': 'Session not found'})
    db.run('DELETE FROM sessions WHERE session_id = ?', (req.params['id'],))
    res.status(204).send()


def start_session(req, res, next_):
    session = db.get('SELECT * FROM sessions WHERE session_id = ? AND user_id = ?', (req.params['id'], req.user_id))
    if not session:
        return res.status(404).json({'error': 'Session not found'})
    db.run("UPDATE sessions SET status = 'in_progress', started_at = datetime('now') WHERE session_id = ?", (req.params['id'],))
    res.json(db.get('SELECT * FROM sessions WHERE session_id = ?', (req.params['id'],)))


def complete_session(req, res, next_):
    # Covers both "mark completed" and "end early" - both save whatever
    # actual_duration_minutes the timer reports and close out the session.
    session = db.get('SELECT * FROM sessions WHERE session_id = ? AND user_id = ?', (req.params['id'], req.user_id))
    if not session:
        return res.status(404).json({'error': 'Session not found'})

    body = req.body or {}
    actual = body.get('actual_duration_minutes')
    if not isinstance(actual, (int, float)) or isinstance(actual, bool):
        actual = session['duration_minutes']

    db.run(
        "UPDATE sessions SET status = 'completed', completed_at = datetime('now'), actual_duration_minutes = ? WHERE session_id = ?",
        (actual, req.params['id']),
    )
    res.json(db.get('SELECT * FROM sessions WHERE session_id = ?', (req.params['id'],)))


def generate(req, res, next_):
    # See src/services/planner_service.py for the actual weighting and scheduling logic.
    res.status(201).json(generate_timetable(req.user_id))
