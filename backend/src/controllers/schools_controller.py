import uuid

from ..config.db import db
from ..lib.http_kit import HttpError
from ..utils.codes import generate_join_code
from ..utils.validators import is_non_empty_string, within_max_length


def _unique_join_code():
    for _ in range(20):
        code = generate_join_code()
        if not db.get('SELECT school_id FROM schools WHERE join_code = ?', (code,)):
            return code
    raise HttpError(500, 'Could not generate a unique join code - try again')


def _require_membership(school_id, user_id):
    member = db.get('SELECT * FROM school_members WHERE school_id = ? AND user_id = ?', (school_id, user_id))
    if not member:
        raise HttpError(404, 'School not found')
    return member


def _require_admin(school_id, user_id):
    member = _require_membership(school_id, user_id)
    if member['role'] != 'admin':
        raise HttpError(403, 'Only a school admin can do this')
    return member


def list_schools(req, res, next_):
    res.json(db.all(
        '''SELECT s.*, m.role FROM schools s
           JOIN school_members m ON m.school_id = s.school_id
           WHERE m.user_id = ? ORDER BY s.created_at DESC''',
        (req.user_id,),
    ))


def create_school(req, res, next_):
    name = (req.body or {}).get('name')
    if not is_non_empty_string(name):
        return res.status(400).json({'error': 'name is required'})
    if not within_max_length(name, 'school_name'):
        return res.status(400).json({'error': 'name is too long (150 characters max)'})

    school_id = str(uuid.uuid4())
    join_code = _unique_join_code()
    db.run('INSERT INTO schools (school_id, name, join_code, created_by) VALUES (?, ?, ?, ?)',
           (school_id, name.strip(), join_code, req.user_id))
    db.run('INSERT INTO school_members (school_id, user_id, role) VALUES (?, ?, ?)', (school_id, req.user_id, 'admin'))
    res.status(201).json(db.get('SELECT * FROM schools WHERE school_id = ?', (school_id,)))


def join_school(req, res, next_):
    join_code = (req.body or {}).get('join_code')
    if not is_non_empty_string(join_code):
        return res.status(400).json({'error': 'join_code is required'})

    school = db.get('SELECT * FROM schools WHERE join_code = ?', (join_code.strip().upper(),))
    if not school:
        return res.status(404).json({'error': 'No school found for that join code'})

    if db.get('SELECT 1 FROM school_members WHERE school_id = ? AND user_id = ?', (school['school_id'], req.user_id)):
        return res.status(400).json({'error': 'You are already a member of this school'})

    db.run('INSERT INTO school_members (school_id, user_id, role) VALUES (?, ?, ?)', (school['school_id'], req.user_id, 'student'))
    res.status(201).json(school)


def get_school(req, res, next_):
    school_id = req.params['id']
    membership = _require_membership(school_id, req.user_id)
    school = db.get('SELECT * FROM schools WHERE school_id = ?', (school_id,))

    members = db.all(
        '''SELECT u.user_id, u.name, m.role, m.joined_at
           FROM school_members m JOIN users u ON u.user_id = m.user_id
           WHERE m.school_id = ? ORDER BY m.joined_at''',
        (school_id,),
    )
    if membership['role'] == 'admin':
        for member in members:
            member['completed_sessions'] = db.get(
                "SELECT COUNT(*) AS c FROM sessions WHERE user_id = ? AND status = 'completed'", (member['user_id'],),
            )['c']

    res.json({**school, 'members': members, 'your_role': membership['role']})


def leave_school(req, res, next_):
    school_id = req.params['id']
    membership = _require_membership(school_id, req.user_id)

    other_members = db.all('SELECT * FROM school_members WHERE school_id = ? AND user_id != ?', (school_id, req.user_id))
    other_admins = [m for m in other_members if m['role'] == 'admin']

    if membership['role'] == 'admin' and other_members and not other_admins:
        return res.status(400).json({'error': 'Promote another member to admin before you leave, or delete the school instead'})

    db.run('DELETE FROM school_members WHERE school_id = ? AND user_id = ?', (school_id, req.user_id))
    if not other_members:
        db.run('DELETE FROM schools WHERE school_id = ?', (school_id,))

    res.status(204).send()


def delete_school(req, res, next_):
    school_id = req.params['id']
    _require_admin(school_id, req.user_id)
    db.run('DELETE FROM schools WHERE school_id = ?', (school_id,))
    res.status(204).send()


def remove_member(req, res, next_):
    school_id = req.params['id']
    _require_admin(school_id, req.user_id)

    target_id = req.params['userId']
    if target_id == req.user_id:
        return res.status(400).json({'error': 'Use leave instead of removing yourself'})

    result = db.run('DELETE FROM school_members WHERE school_id = ? AND user_id = ?', (school_id, target_id))
    if result['changes'] == 0:
        return res.status(404).json({'error': 'That user is not a member of this school'})
    res.status(204).send()


def create_announcement(req, res, next_):
    school_id = req.params['id']
    _require_admin(school_id, req.user_id)

    body = req.body or {}
    title, text = body.get('title'), body.get('body')
    if not is_non_empty_string(title) or not is_non_empty_string(text):
        return res.status(400).json({'error': 'title and body are required'})
    if not within_max_length(title, 'announcement_title'):
        return res.status(400).json({'error': 'title is too long (150 characters max)'})
    if not within_max_length(text, 'announcement_body'):
        return res.status(400).json({'error': 'body is too long (4000 characters max)'})

    announcement_id = str(uuid.uuid4())
    db.run(
        'INSERT INTO school_announcements (announcement_id, school_id, posted_by, title, body) VALUES (?, ?, ?, ?, ?)',
        (announcement_id, school_id, req.user_id, title.strip(), text.strip()),
    )
    res.status(201).json(db.get('SELECT * FROM school_announcements WHERE announcement_id = ?', (announcement_id,)))


def list_announcements(req, res, next_):
    school_id = req.params['id']
    _require_membership(school_id, req.user_id)
    res.json(db.all(
        'SELECT * FROM school_announcements WHERE school_id = ? ORDER BY created_at DESC', (school_id,),
    ))
