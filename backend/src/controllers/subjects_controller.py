import uuid

from ..config.db import db
from ..utils.validators import is_non_empty_string, is_valid_difficulty, within_max_length


def list_subjects(req, res, next_):
    res.json(db.all('SELECT * FROM subjects WHERE user_id = ? ORDER BY created_at', (req.user_id,)))


def create_subject(req, res, next_):
    body = req.body or {}
    subject_name, difficulty = body.get('subject_name'), body.get('difficulty')

    if not is_non_empty_string(subject_name):
        return res.status(400).json({'error': 'subject_name is required'})
    if not within_max_length(subject_name, 'subject_name'):
        return res.status(400).json({'error': 'subject_name is too long (100 characters max)'})
    if difficulty is not None and not is_valid_difficulty(difficulty):
        return res.status(400).json({'error': 'difficulty must be easy, medium, or hard'})

    subject_id = str(uuid.uuid4())
    db.run(
        'INSERT INTO subjects (subject_id, user_id, subject_name, difficulty) VALUES (?, ?, ?, ?)',
        (subject_id, req.user_id, subject_name.strip(), difficulty or 'medium'),
    )
    res.status(201).json(db.get('SELECT * FROM subjects WHERE subject_id = ?', (subject_id,)))


def update_subject(req, res, next_):
    subject = db.get('SELECT * FROM subjects WHERE subject_id = ? AND user_id = ?', (req.params['id'], req.user_id))
    if not subject:
        return res.status(404).json({'error': 'Subject not found'})

    body = req.body or {}
    subject_name, difficulty = body.get('subject_name'), body.get('difficulty')
    if subject_name is not None and not within_max_length(subject_name, 'subject_name'):
        return res.status(400).json({'error': 'subject_name is too long (100 characters max)'})
    if difficulty is not None and not is_valid_difficulty(difficulty):
        return res.status(400).json({'error': 'difficulty must be easy, medium, or hard'})

    db.run(
        'UPDATE subjects SET subject_name = COALESCE(?, subject_name), difficulty = COALESCE(?, difficulty) WHERE subject_id = ?',
        (subject_name, difficulty, req.params['id']),
    )
    res.json(db.get('SELECT * FROM subjects WHERE subject_id = ?', (req.params['id'],)))


def delete_subject(req, res, next_):
    subject = db.get('SELECT * FROM subjects WHERE subject_id = ? AND user_id = ?', (req.params['id'], req.user_id))
    if not subject:
        return res.status(404).json({'error': 'Subject not found'})
    db.run('DELETE FROM subjects WHERE subject_id = ?', (req.params['id'],))
    res.status(204).send()
