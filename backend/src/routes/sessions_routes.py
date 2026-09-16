from ..controllers.sessions_controller import (
    complete_session,
    create_session,
    delete_session,
    generate,
    get_one,
    list_sessions,
    start_session,
    update_session,
)
from ..lib.http_kit import create_router
from ..middleware.auth_middleware import authenticate

router = create_router()
router.use(authenticate)
router.post('/generate', generate)  # Smart Planner: build/rebuild the timetable
router.get('/', list_sessions)
router.post('/', create_session)  # add a session manually
router.get('/:id', get_one)
router.patch('/:id', update_session)  # edit / reschedule
router.delete('/:id', delete_session)
router.post('/:id/start', start_session)
router.post('/:id/complete', complete_session)  # mark completed or end early
