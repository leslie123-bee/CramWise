from ..controllers.subjects_controller import create_subject, delete_subject, list_subjects, update_subject
from ..lib.http_kit import create_router
from ..middleware.auth_middleware import authenticate

router = create_router()
router.use(authenticate)
router.get('/', list_subjects)
router.post('/', create_subject)
router.patch('/:id', update_subject)
router.delete('/:id', delete_subject)
