from ..services.missed_sessions_service import mark_missed_sessions
from ..services.progress_service import get_progress


def get(req, res, next_):
    mark_missed_sessions()
    res.json(get_progress(req.user_id))
