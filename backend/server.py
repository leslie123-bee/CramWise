import os
import threading

from src.config.env import load_env

load_env()  # must run before src.app pulls in src.config.db, which reads DB_PATH

from src.app import app
from src.services.missed_sessions_service import mark_missed_sessions

PORT = int(os.environ.get('PORT', 4000))
SWEEP_INTERVAL_SECONDS = 15 * 60

_INSECURE_SECRETS = {'', 'change-this-to-a-long-random-string'}


def _check_jwt_secret():
    # A weak/default JWT_SECRET means anyone who saw this file (or the
    # public .env.example) could forge a valid login token for any
    # account. This only warns by default so local testing on your own
    # computer keeps working without interruption - set
    # REQUIRE_STRONG_SECRET=1 in .env to make it a hard error instead,
    # which is worth doing before this runs anywhere but your own laptop.
    secret = os.environ.get('JWT_SECRET', '')
    if secret in _INSECURE_SECRETS or len(secret) < 16:
        print('\n' + '!' * 66)
        print('! WARNING: JWT_SECRET in .env is missing, short, or the example')
        print('! placeholder. Anyone who saw this file could forge login tokens.')
        print('! Fix: open .env and set JWT_SECRET to a long random string, e.g.')
        print('!   python3 -c "import secrets; print(secrets.token_hex(32))"')
        print('! Starting anyway so local testing keeps working. To make this a')
        print('! hard error instead (recommended before running this anywhere')
        print('! other than your own computer), set REQUIRE_STRONG_SECRET=1.')
        print('!' * 66 + '\n')
        if os.environ.get('REQUIRE_STRONG_SECRET') == '1':
            raise SystemExit(1)


def _sweep_loop():
    # Periodic sweep: flips overdue 'not_started' sessions to 'missed' even
    # if nobody happens to hit an endpoint that would trigger it lazily.
    stop = threading.Event()
    while not stop.wait(SWEEP_INTERVAL_SECONDS):
        try:
            changed = mark_missed_sessions()
            if changed:
                print(f'Missed-session sweep: marked {changed} session(s) as missed')
        except Exception as err:
            print('Missed-session sweep failed:', err)


if __name__ == '__main__':
    _check_jwt_secret()
    threading.Thread(target=_sweep_loop, daemon=True).start()
    print(f'Student Planner API listening on http://localhost:{PORT}')
    app.listen(PORT)
