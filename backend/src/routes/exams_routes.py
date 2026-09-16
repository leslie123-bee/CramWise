from ..controllers.exams_controller import create_exam, delete_exam, list_exams, update_exam
from ..lib.http_kit import create_router
from ..middleware.auth_middleware import authenticate

router = create_router()
router.use(authenticate)
router.get('/', list_exams)
router.post('/', create_exam)
router.patch('/:id', update_exam)
router.delete('/:id', delete_exam)
