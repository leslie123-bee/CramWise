from ..controllers.quizzes_controller import create_quiz, delete_quiz, get_quiz, list_quizzes
from ..lib.http_kit import create_router
from ..middleware.auth_middleware import authenticate

router = create_router()
router.use(authenticate)
router.get('/', list_quizzes)
router.post('/generate', create_quiz)
router.get('/:id', get_quiz)
router.delete('/:id', delete_quiz)
