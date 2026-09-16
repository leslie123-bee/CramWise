import uuid

from ..config.db import db
from ..utils.validators import is_non_empty_string, is_valid_date, within_max_length


def list_exams(req, res, next_):
    res.json(db.all('SELECT * FROM exams WHERE user_id = ? ORDER BY exam_date', (req.user_id,)))


def create_exam(req, res, next_):
    body = req.body or {}
    subject_id, exam_name, exam_date = body.get('subject_id'), body.get('exam_name'), body.get('exam_date')

    if not is_non_empty_string(subject_id) or not is_non_empty_string(exam_name) or not is_valid_date(exam_date):
        return res.status(400).json({'error': 'subject_id, exam_name, and a valid exam_date (YYYY-MM-DD) are required'})
    if not within_max_length(exam_name, 'exam_name'):
        return res.status(400).json({'error': 'exam_name is too long (150 characters max)'})

    subject = db.get('SELECT * FROM subjects WHERE subject_id = ? AND user_id = ?', (subject_id, req.user_id))
    if not subject:
        return res.status(404).json({'error': 'Subject not found'})

    exam_id = str(uuid.uuid4())
    db.run(
        'INSERT INTO exams (exam_id, user_id, subject_id, exam_name, exam_date) VALUES (?, ?, ?, ?, ?)',
        (exam_id, req.user_id, subject_id, exam_name.strip(), exam_date),
    )
    res.status(201).json(db.get('SELECT * FROM exams WHERE exam_id = ?', (exam_id,)))


def update_exam(req, res, next_):
    exam = db.get('SELECT * FROM exams WHERE exam_id = ? AND user_id = ?', (req.params['id'], req.user_id))
    if not exam:
        return res.status(404).json({'error': 'Exam not found'})

    body = req.body or {}
    exam_name, exam_date = body.get('exam_name'), body.get('exam_date')
    if exam_name is not None and not within_max_length(exam_name, 'exam_name'):
        return res.status(400).json({'error': 'exam_name is too long (150 characters max)'})
    if exam_date is not None and not is_valid_date(exam_date):
        return res.status(400).json({'error': 'exam_date must be a valid date (YYYY-MM-DD)'})

    db.run(
        'UPDATE exams SET exam_name = COALESCE(?, exam_name), exam_date = COALESCE(?, exam_date) WHERE exam_id = ?',
        (exam_name, exam_date, req.params['id']),
    )
    res.json(db.get('SELECT * FROM exams WHERE exam_id = ?', (req.params['id'],)))


def delete_exam(req, res, next_):
    exam = db.get('SELECT * FROM exams WHERE exam_id = ? AND user_id = ?', (req.params['id'], req.user_id))
    if not exam:
        return res.status(404).json({'error': 'Exam not found'})
    db.run('DELETE FROM exams WHERE exam_id = ?', (req.params['id'],))
    res.status(204).send()
