import json
import uuid

from ..config.db import db
from ..utils.ai_client import generate_quiz, is_configured
from ..utils.validators import is_non_empty_string, within_max_length


def _row_to_quiz(row):
    row = dict(row)
    row['questions'] = json.loads(row['questions'])
    return row


def create_quiz(req, res, next_):
    body = req.body or {}
    subject_id = body.get('subject_id')
    topic = body.get('topic')
    num_questions = body.get('num_questions')
    if not isinstance(num_questions, int) or num_questions < 1:
        num_questions = 5
    num_questions = min(num_questions, 15)

    if not is_non_empty_string(subject_id):
        return res.status(400).json({'error': 'subject_id is required'})
    if topic is not None and not within_max_length(topic, 'topic'):
        return res.status(400).json({'error': 'topic is too long (150 characters max)'})

    subject = db.get('SELECT * FROM subjects WHERE subject_id = ? AND user_id = ?', (subject_id, req.user_id))
    if not subject:
        return res.status(404).json({'error': 'Subject not found'})

    questions = generate_quiz(subject['subject_name'], topic, num_questions)

    quiz_id = str(uuid.uuid4())
    db.run(
        'INSERT INTO quizzes (quiz_id, user_id, subject_id, topic, questions) VALUES (?, ?, ?, ?, ?)',
        (quiz_id, req.user_id, subject_id, topic, json.dumps(questions)),
    )
    res.status(201).json({
        **_row_to_quiz(db.get('SELECT * FROM quizzes WHERE quiz_id = ?', (quiz_id,))),
        'ai_connected': is_configured(),
    })


def list_quizzes(req, res, next_):
    # Computed in Python rather than with SQLite's json_array_length() so
    # this doesn't depend on the JSON1 extension being compiled into
    # whichever Python/SQLite build happens to be running this.
    rows = db.all(
        '''SELECT q.quiz_id, q.subject_id, s.subject_name, q.topic, q.created_at, q.questions
           FROM quizzes q JOIN subjects s ON s.subject_id = q.subject_id
           WHERE q.user_id = ? ORDER BY q.created_at DESC''',
        (req.user_id,),
    )
    for row in rows:
        row['question_count'] = len(json.loads(row.pop('questions')))
    res.json(rows)


def get_quiz(req, res, next_):
    row = db.get('SELECT * FROM quizzes WHERE quiz_id = ? AND user_id = ?', (req.params['id'], req.user_id))
    if not row:
        return res.status(404).json({'error': 'Quiz not found'})
    res.json(_row_to_quiz(row))


def delete_quiz(req, res, next_):
    row = db.get('SELECT * FROM quizzes WHERE quiz_id = ? AND user_id = ?', (req.params['id'], req.user_id))
    if not row:
        return res.status(404).json({'error': 'Quiz not found'})
    db.run('DELETE FROM quizzes WHERE quiz_id = ?', (req.params['id'],))
    res.status(204).send()
