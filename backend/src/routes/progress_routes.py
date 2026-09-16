from ..controllers.progress_controller import get
from ..lib.http_kit import create_router
from ..middleware.auth_middleware import authenticate

router = create_router()
router.use(authenticate)
router.get('/', get)
