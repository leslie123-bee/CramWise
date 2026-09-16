from ..controllers.groups_controller import (
    create_group,
    delete_group,
    get_group,
    join_group,
    leave_group,
    list_groups,
    remove_member,
)
from ..lib.http_kit import create_router
from ..middleware.auth_middleware import authenticate

router = create_router()
router.use(authenticate)
router.get('/', list_groups)
router.post('/', create_group)
router.post('/join', join_group)
router.get('/:id', get_group)
router.post('/:id/leave', leave_group)
router.delete('/:id', delete_group)
router.delete('/:id/members/:userId', remove_member)
