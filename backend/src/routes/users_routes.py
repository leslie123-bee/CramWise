from ..controllers.users_controller import get_me, update_me, update_password
from ..lib.http_kit import create_router
from ..middleware.auth_middleware import authenticate

router = create_router()
router.use(authenticate)
router.get('/me', get_me)
router.patch('/me', update_me)
router.patch('/me/password', update_password)
