import json

from ..config.db import db
from ..utils.validators import is_valid_days_array, is_valid_period, within_max_length
from .auth_controller import get_user, public_user


def get_me(req, res, next_):
    res.json(public_user(get_user(req.user_id)))


def update_me(req, res, next_):
    if not get_user(req.user_id):
        return res.status(404).json({'error': 'User not found'})

    body = req.body or {}
    name = body.get('name')
    study_goal = body.get('study_goal')
    preferred_study_time = body.get('preferred_study_time')
    available_days = body.get('available_days')
    profile_picture = body.get('profile_picture')

    if name is not None and not within_max_length(name, 'name'):
        return res.status(400).json({'error': 'name is too long (100 characters max)'})
    if study_goal is not None and not within_max_length(study_goal, 'study_goal'):
        return res.status(400).json({'error': 'study_goal is too long (300 characters max)'})
    if preferred_study_time is not None and not is_valid_period(preferred_study_time):
        return res.status(400).json({'error': 'preferred_study_time must be morning, afternoon, or evening'})
    if available_days is not None and not is_valid_days_array(available_days):
        return res.status(400).json({'error': 'available_days must be a non-empty array of mon/tue/wed/thu/fri/sat/sun'})

    db.run(
        '''UPDATE users SET
             name = COALESCE(?, name),
             study_goal = COALESCE(?, study_goal),
             preferred_study_time = COALESCE(?, preferred_study_time),
             available_days = COALESCE(?, available_days),
             profile_picture = COALESCE(?, profile_picture)
           WHERE user_id = ?''',
        (
            name,
            study_goal,
            preferred_study_time,
            json.dumps(available_days) if available_days is not None else None,
            profile_picture,
            req.user_id,
        ),
    )
    res.json(public_user(get_user(req.user_id)))
