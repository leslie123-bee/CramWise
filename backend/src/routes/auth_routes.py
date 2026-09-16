from ..controllers.auth_controller import login, register
from ..lib.http_kit import create_router
from ..middleware.rate_limit_middleware import rate_limit_auth

router = create_router()
router.use(rate_limit_auth)
router.post('/register', register)
router.post('/login', login)
