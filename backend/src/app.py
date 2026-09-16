from .lib.http_kit import create_app
from .routes.auth_routes import router as auth_router
from .routes.exams_routes import router as exams_router
from .routes.groups_routes import router as groups_router
from .routes.progress_routes import router as progress_router
from .routes.quizzes_routes import router as quizzes_router
from .routes.schools_routes import router as schools_router
from .routes.sessions_routes import router as sessions_router
from .routes.subjects_routes import router as subjects_router
from .routes.tutor_routes import router as tutor_router
from .routes.users_routes import router as users_router


def _health(req, res, next_):
    res.json({'status': 'ok'})


app = create_app()
app.get('/health', _health)

app.mount('/api/auth', auth_router)
app.mount('/api/users', users_router)
app.mount('/api/subjects', subjects_router)
app.mount('/api/exams', exams_router)
app.mount('/api/sessions', sessions_router)
app.mount('/api/progress', progress_router)
app.mount('/api/groups', groups_router)
app.mount('/api/schools', schools_router)
app.mount('/api/quizzes', quizzes_router)
app.mount('/api/tutor', tutor_router)
