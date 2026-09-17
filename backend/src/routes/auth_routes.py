from ..controllers.auth_controller import forgot_password, login, register, reset_password
from ..lib.http_kit import create_router
from ..middleware.rate_limit_middleware import rate_limit_auth

router = create_router()
router.use(rate_limit_auth)
router.post('/register', register)
router.post('/login', login)
router.post('/forgot-password', forgot_password)
router.post('/reset-password', reset_password)
