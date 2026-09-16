# Short, human-typeable join codes for study groups and schools, e.g.
# "7F3KQL". Deliberately skips 0/O/1/I so nobody mis-types a code read
# off a phone screen.
import random

_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generate_join_code(length=6):
    return ''.join(random.choice(_ALPHABET) for _ in range(length))
