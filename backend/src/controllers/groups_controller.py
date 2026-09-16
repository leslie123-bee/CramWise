import uuid

from ..config.db import db
from ..lib.http_kit import HttpError
from ..utils.codes import generate_join_code
from ..utils.validators import is_non_empty_string, within_max_length


def _unique_join_code():
    for _ in range(20):
        code = generate_join_code()
        if not db.get('SELECT group_id FROM study_groups WHERE join_code = ?', (code,)):
            return code
    raise HttpError(500, 'Could not generate a unique join code - try again')


def _require_membership(group_id, user_id):
    member = db.get('SELECT * FROM group_members WHERE group_id = ? AND user_id = ?', (group_id, user_id))
    if not member:
        raise HttpError(404, 'Study group not found')
    return member


def list_groups(req, res, next_):
    res.json(db.all(
        '''SELECT g.*, m.role FROM study_groups g
           JOIN group_members m ON m.group_id = g.group_id
           WHERE m.user_id = ? ORDER BY g.created_at DESC''',
        (req.user_id,),
    ))


def create_group(req, res, next_):
    name = (req.body or {}).get('name')
    if not is_non_empty_string(name):
        return res.status(400).json({'error': 'name is required'})
    if not within_max_length(name, 'group_name'):
        return res.status(400).json({'error': 'name is too long (100 characters max)'})

    group_id = str(uuid.uuid4())
    join_code = _unique_join_code()
    db.run('INSERT INTO study_groups (group_id, name, join_code, created_by) VALUES (?, ?, ?, ?)',
           (group_id, name.strip(), join_code, req.user_id))
    db.run('INSERT INTO group_members (group_id, user_id, role) VALUES (?, ?, ?)', (group_id, req.user_id, 'owner'))
    res.status(201).json(db.get('SELECT * FROM study_groups WHERE group_id = ?', (group_id,)))


def join_group(req, res, next_):
    join_code = (req.body or {}).get('join_code')
    if not is_non_empty_string(join_code):
        return res.status(400).json({'error': 'join_code is required'})

    group = db.get('SELECT * FROM study_groups WHERE join_code = ?', (join_code.strip().upper(),))
    if not group:
        return res.status(404).json({'error': 'No study group found for that join code'})

    if db.get('SELECT 1 FROM group_members WHERE group_id = ? AND user_id = ?', (group['group_id'], req.user_id)):
        return res.status(400).json({'error': 'You are already a member of this group'})

    db.run('INSERT INTO group_members (group_id, user_id, role) VALUES (?, ?, ?)', (group['group_id'], req.user_id, 'member'))
    res.status(201).json(group)


def get_group(req, res, next_):
    group_id = req.params['id']
    _require_membership(group_id, req.user_id)
    group = db.get('SELECT * FROM study_groups WHERE group_id = ?', (group_id,))

    members = db.all(
        '''SELECT u.user_id, u.name, m.role, m.joined_at
           FROM group_members m JOIN users u ON u.user_id = m.user_id
           WHERE m.group_id = ? ORDER BY m.joined_at''',
        (group_id,),
    )
    for member in members:
        member['completed_sessions'] = db.get(
            "SELECT COUNT(*) AS c FROM sessions WHERE user_id = ? AND status = 'completed'", (member['user_id'],),
        )['c']

    res.json({**group, 'members': members})


def leave_group(req, res, next_):
    group_id = req.params['id']
    membership = _require_membership(group_id, req.user_id)
    remaining = db.all(
        'SELECT * FROM group_members WHERE group_id = ? AND user_id != ? ORDER BY joined_at',
        (group_id, req.user_id),
    )

    if membership['role'] == 'owner' and remaining:
        db.run('UPDATE group_members SET role = ? WHERE group_id = ? AND user_id = ?',
               ('owner', group_id, remaining[0]['user_id']))

    db.run('DELETE FROM group_members WHERE group_id = ? AND user_id = ?', (group_id, req.user_id))
    if not remaining:
        db.run('DELETE FROM study_groups WHERE group_id = ?', (group_id,))

    res.status(204).send()


def delete_group(req, res, next_):
    group_id = req.params['id']
    membership = _require_membership(group_id, req.user_id)
    if membership['role'] != 'owner':
        return res.status(403).json({'error': 'Only the group owner can delete this group'})
    db.run('DELETE FROM study_groups WHERE group_id = ?', (group_id,))
    res.status(204).send()


def remove_member(req, res, next_):
    group_id = req.params['id']
    membership = _require_membership(group_id, req.user_id)
    if membership['role'] != 'owner':
        return res.status(403).json({'error': 'Only the group owner can remove members'})

    target_id = req.params['userId']
    if target_id == req.user_id:
        return res.status(400).json({'error': 'Use leave instead of removing yourself'})

    result = db.run('DELETE FROM group_members WHERE group_id = ? AND user_id = ?', (group_id, target_id))
    if result['changes'] == 0:
        return res.status(404).json({'error': 'That user is not a member of this group'})
    res.status(204).send()
