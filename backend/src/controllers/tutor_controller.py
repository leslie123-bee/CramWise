import uuid

from ..config.db import db
from ..utils.ai_client import is_configured, tutor_reply
from ..utils.validators import is_non_empty_string, within_max_length

HISTORY_LIMIT = 20  # how many past messages get sent as conversation context


def ask(req, res, next_):
    body = req.body or {}
    message, subject_id = body.get('message'), body.get('subject_id')

    if not is_non_empty_string(message):
        return res.status(400).json({'error': 'message is required'})
    if not within_max_length(message, 'tutor_message'):
        return res.status(400).json({'error': 'message is too long (4000 characters max)'})

    subject_name = 'your studies'
    if subject_id is not None:
        subject = db.get('SELECT * FROM subjects WHERE subject_id = ? AND user_id = ?', (subject_id, req.user_id))
        if not subject:
            return res.status(404).json({'error': 'Subject not found'})
        subject_name = subject['subject_name']

    query = 'SELECT role, content FROM tutor_messages WHERE user_id = ?'
    params = [req.user_id]
    if subject_id is not None:
        query += ' AND subject_id = ?'
        params.append(subject_id)
    query += ' ORDER BY created_at DESC LIMIT ?'
    params.append(HISTORY_LIMIT)
    history = list(reversed(db.all(query, tuple(params))))

    user_message_id = str(uuid.uuid4())
    db.run(
        'INSERT INTO tutor_messages (message_id, user_id, subject_id, role, content) VALUES (?, ?, ?, ?, ?)',
        (user_message_id, req.user_id, subject_id, 'user', message.strip()),
    )

    conversation = history + [{'role': 'user', 'content': message.strip()}]
    reply_text = tutor_reply(subject_name, conversation)

    reply_id = str(uuid.uuid4())
    db.run(
        'INSERT INTO tutor_messages (message_id, user_id, subject_id, role, content) VALUES (?, ?, ?, ?, ?)',
        (reply_id, req.user_id, subject_id, 'assistant', reply_text),
    )

    res.status(201).json({
        'reply': db.get('SELECT * FROM tutor_messages WHERE message_id = ?', (reply_id,)),
        'ai_connected': is_configured(),
    })


def list_messages(req, res, next_):
    query = 'SELECT * FROM tutor_messages WHERE user_id = ?'
    params = [req.user_id]
    if req.query.get('subject_id'):
        query += ' AND subject_id = ?'
        params.append(req.query['subject_id'])
    query += ' ORDER BY created_at'
    res.json(db.all(query, tuple(params)))


def clear_messages(req, res, next_):
    query = 'DELETE FROM tutor_messages WHERE user_id = ?'
    params = [req.user_id]
    if req.query.get('subject_id'):
        query += ' AND subject_id = ?'
        params.append(req.query['subject_id'])
    db.run(query, tuple(params))
    res.status(204).send()
