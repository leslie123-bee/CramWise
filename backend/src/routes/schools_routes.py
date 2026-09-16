from ..controllers.schools_controller import (
    create_announcement,
    create_school,
    delete_school,
    get_school,
    join_school,
    leave_school,
    list_announcements,
    list_schools,
    remove_member,
)
from ..lib.http_kit import create_router
from ..middleware.auth_middleware import authenticate

router = create_router()
router.use(authenticate)
router.get('/', list_schools)
router.post('/', create_school)
router.post('/join', join_school)
router.get('/:id', get_school)
router.post('/:id/leave', leave_school)
router.delete('/:id', delete_school)
router.delete('/:id/members/:userId', remove_member)
router.post('/:id/announcements', create_announcement)
router.get('/:id/announcements', list_announcements)
