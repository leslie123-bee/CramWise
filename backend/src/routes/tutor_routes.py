from ..controllers.tutor_controller import ask, clear_messages, list_messages
from ..lib.http_kit import create_router
from ..middleware.auth_middleware import authenticate

router = create_router()
router.use(authenticate)
router.post('/ask', ask)
router.get('/messages', list_messages)
router.delete('/messages', clear_messages)
