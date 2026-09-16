# A minimal Flask-alike built only on Python's built-in http.server
# module, so the backend runs with zero pip installs. Supports what this
# app needs: router.get/post/patch/delete(path, handler),
# router.use(middleware), :param path segments, req.params/query/body,
# res.status().json(), and an error chain via next(err) - shaped closely
# enough to a real framework that swapping to Flask later (see the
# README) barely touches the routes/controllers.
import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs, unquote

# Nothing in this app's API needs a request body anywhere close to this
# size - it's here purely as a safety net so a huge (accidental or
# malicious) request body can't be used to exhaust memory.
MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MB


class HttpError(Exception):
    """Raise this from a controller/service to send a specific status code,
    e.g. raise HttpError(404, 'Subject not found')."""
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def _compile_path(full_path):
    segments = [s for s in full_path.split('/') if s]
    keys = []
    parts = []
    for seg in segments:
        if seg.startswith(':'):
            keys.append(seg[1:])
            parts.append('([^/]+)')
        else:
            parts.append(re.escape(seg))
    pattern = '/'.join(parts)
    regex = re.compile('^/' + pattern + '/?$') if pattern else re.compile('^/?$')
    return regex, keys


class Request:
    def __init__(self, method, path, query, body, headers, ip=None):
        self.method = method
        self.path = path
        self.query = query or {}
        self.body = body if isinstance(body, dict) else {}
        self.headers = headers or {}  # lower-cased keys
        self.params = {}
        self.user_id = None  # set by the auth middleware
        self.ip = ip  # the connecting client's address, for rate limiting


class Response:
    def __init__(self):
        self.status_code = 200
        self.body = b''
        self.sent = False

    def status(self, code):
        self.status_code = code
        return self

    def json(self, obj):
        self.body = json.dumps(obj).encode('utf-8') if obj is not None else b''
        self.sent = True
        return self

    def send(self, text=None):
        if text is None:
            self.body = b''
        elif isinstance(text, (dict, list)):
            self.body = json.dumps(text).encode('utf-8')
        else:
            self.body = str(text).encode('utf-8')
        self.sent = True
        return self


class Router:
    def __init__(self):
        self.routes = []
        self._middlewares = []

    def use(self, fn):
        self._middlewares.append(fn)
        return self

    def _add(self, method, path, handlers):
        self.routes.append({'method': method, 'path': path, 'handlers': [*self._middlewares, *handlers]})
        return self

    def get(self, path, *h): return self._add('GET', path, h)
    def post(self, path, *h): return self._add('POST', path, h)
    def patch(self, path, *h): return self._add('PATCH', path, h)
    def delete(self, path, *h): return self._add('DELETE', path, h)


class App:
    def __init__(self):
        self.compiled_routes = []

    def mount(self, prefix, router):
        base = prefix.rstrip('/')
        for r in router.routes:
            full = (base + (r['path'] if r['path'] != '/' else '')) or '/'
            regex, keys = _compile_path(full)
            self.compiled_routes.append({'method': r['method'], 'regex': regex, 'keys': keys, 'handlers': r['handlers']})

    def get(self, path, *h):
        regex, keys = _compile_path(path)
        self.compiled_routes.append({'method': 'GET', 'regex': regex, 'keys': keys, 'handlers': list(h)})

    def _find(self, method, pathname):
        for r in self.compiled_routes:
            if r['method'] != method:
                continue
            m = r['regex'].match(pathname)
            if m:
                return r, m
        return None, None

    def handle(self, raw_handler, method):
        started = time.time()
        parsed = urlsplit(raw_handler.path)
        pathname = unquote(parsed.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        headers = {k.lower(): v for k, v in raw_handler.headers.items()}

        if method == 'OPTIONS':
            self._send(raw_handler, 204, b'')
            return

        try:
            length = int(raw_handler.headers.get('Content-Length', 0) or 0)
        except Exception:
            length = 0

        if length > MAX_BODY_BYTES:
            self._send(raw_handler, 413, json.dumps({'error': 'Request body is too large'}).encode('utf-8'))
            return

        try:
            raw_body = raw_handler.rfile.read(length) if length else b''
            body = json.loads(raw_body) if raw_body.strip() else {}
        except Exception:
            self._send(raw_handler, 400, json.dumps({'error': 'Request body must be valid JSON'}).encode('utf-8'))
            return

        client_ip = raw_handler.client_address[0] if raw_handler.client_address else None
        req = Request(method, pathname, query, body, headers, ip=client_ip)
        res = Response()
        route, match = self._find(method, pathname)
        status_for_log = None

        if not route:
            self._send(raw_handler, 404, json.dumps({'error': f'Route not found: {method} {pathname}'}).encode('utf-8'))
            status_for_log = 404
        else:
            req.params = {key: unquote(val) for key, val in zip(route['keys'], match.groups())}
            try:
                self._run_chain(route['handlers'], req, res)
                self._send(raw_handler, res.status_code, res.body)
                status_for_log = res.status_code
            except HttpError as e:
                self._send(raw_handler, e.status, json.dumps({'error': str(e)}).encode('utf-8'))
                status_for_log = e.status
            except Exception as e:
                print('Unhandled error:', repr(e))
                self._send(raw_handler, 500, json.dumps({'error': 'Internal server error'}).encode('utf-8'))
                status_for_log = 500

        print(f'{method} {pathname} {status_for_log} {int((time.time() - started) * 1000)}ms')

    @staticmethod
    def _run_chain(handlers, req, res):
        index = {'i': 0}

        def next_(err=None):
            if err:
                raise err
            if index['i'] >= len(handlers):
                return
            handler = handlers[index['i']]
            index['i'] += 1
            handler(req, res, next_)

        next_()

    @staticmethod
    def _send(raw_handler, status, payload):
        raw_handler.send_response(status)
        raw_handler.send_header('Access-Control-Allow-Origin', '*')
        raw_handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        raw_handler.send_header('Access-Control-Allow-Methods', 'GET,POST,PATCH,PUT,DELETE,OPTIONS')
        raw_handler.send_header('Content-Type', 'application/json')
        raw_handler.send_header('Content-Length', str(len(payload)))
        # A couple of cheap, standard security headers: stop a browser from
        # "helpfully" guessing this JSON is something else and executing it,
        # and stop this API's responses from ever being framed inside
        # another site.
        raw_handler.send_header('X-Content-Type-Options', 'nosniff')
        raw_handler.send_header('X-Frame-Options', 'DENY')
        raw_handler.end_headers()
        if payload:
            raw_handler.wfile.write(payload)

    def listen(self, port):
        app = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self): app.handle(self, 'GET')
            def do_POST(self): app.handle(self, 'POST')
            def do_PATCH(self): app.handle(self, 'PATCH')
            def do_PUT(self): app.handle(self, 'PUT')
            def do_DELETE(self): app.handle(self, 'DELETE')
            def do_OPTIONS(self): app.handle(self, 'OPTIONS')

            def log_message(self, fmt, *args):
                pass  # App.handle() already logs one line per request

        # ThreadingHTTPServer (stdlib, no new dependency) rather than plain
        # HTTPServer, so one slow request - or two people in the same study
        # group hitting the API at the same time - doesn't block everyone
        # else. src/config/db.py takes a lock around writes so this is safe
        # with SQLite.
        try:
            server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
            server.serve_forever()
        except OSError as e:
            if 'Address already in use' in str(e) or getattr(e, 'errno', None) == 98:
                print(f'\nCould not start: port {port} is already in use.')
                print(f'Something else (maybe another copy of this server) is already running on port {port}.')
                print(f'Either stop that process, or set a different PORT in your .env file and try again.\n')
            else:
                print(f'\nCould not start the server: {e}\n')
            raise SystemExit(1)


def create_app():
    return App()


def create_router():
    return Router()
