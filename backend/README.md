# Student Planner — Backend (Python)

The API behind the Student Planner blueprint: accounts, subjects, exams, the
Smart Planner timetable generator, study sessions, and progress tracking.

This is the Python version — same app, same endpoints, same database
design as the JavaScript version, just written in Python for anyone more
comfortable reading that.

## Stack

- **Python** — no framework (no Flask/Django). The server, routing, JSON
  parsing, and CORS are hand-written in `src/lib/http_kit.py`, styled to
  look and behave like Flask so the code reads the way a normal Flask app
  would.
- **SQLite**, via Python's own built-in `sqlite3` module — the database is
  a single file at `data/planner.db`, created automatically.
- **Python's built-in `hashlib`/`hmac` modules** for password hashing
  (scrypt) and login tokens (an HMAC-signed token — the same idea as a
  JWT).

**This means there is nothing to install.** No `pip install`, no virtual
environment needed — the whole thing runs on what Python already ships
with. You just need Python itself, version **3.9 or newer** (run
`python3 --version` to check; download the latest from
[python.org](https://python.org) if you need to upgrade).

If you'd rather use Flask, bcrypt, and PyJWT instead (the more common way
real-world Python backends are built), that's a reasonable next step once
you're running this on your own computer with normal internet access — see
*Swapping in the standard packages* at the bottom.

## Project layout

```
server.py                          entry point — starts the server + the missed-session sweep
src/app.py                         mounts every route group onto the server
src/lib/http_kit.py                the tiny hand-built stand-in for Flask
src/config/db.py                   opens the SQLite file, applies db/schema.sql
src/config/env.py                  reads .env (stand-in for python-dotenv)
db/schema.sql                      the four tables: users, subjects, exams, sessions
src/routes/                        one file per resource — just URL -> controller wiring
src/controllers/                   one file per resource — request in, response out
src/services/
  planner_service.py               the Smart Planner: builds the timetable
  progress_service.py              the Progress screen's numbers (streak, %s, etc.)
  missed_sessions_service.py       flips overdue sessions to "missed"
src/middleware/auth_middleware.py  checks the login token on every protected route
src/utils/crypto_utils.py          password hashing + token sign/verify (stand-in for bcrypt + PyJWT)
src/utils/validators.py            small input-checking helpers shared everywhere
src/utils/codes.py                 generates the short join codes groups/schools use
src/utils/ai_client.py             the one file the AI quiz + tutor features call into
postman/*.postman_collection.json  every endpoint, ready to import and click through
```

## Running it

```bash
cd student-planner-backend-python
cp .env.example .env          # then open .env and change JWT_SECRET to something random
python3 server.py
```

That's it — no install step. The API is then at `http://localhost:4000`.
`GET /health` returns `{"status":"ok"}` once it's up. The database file
appears in `data/` the first time you run it.

(If your system's Python command is just `python` instead of `python3`,
use that instead.)

## Trying it out (no coding needed)

Install [Postman](https://www.postman.com/downloads/) (free, just an app —
like a browser, but for testing an API instead of a website), then:

1. Open Postman → **Import** → pick
   `postman/student-planner.postman_collection.json`.
2. Click into the collection's variables (top right, the eye icon) and
   you'll see `baseUrl`, `token`, `subjectId`, etc. — empty for now.
3. Run **Auth → Register**. The response includes a `token` — copy it into
   the `token` variable so every later request is automatically logged in.
4. Run **Profile → Complete setup** — sets the study goal, preferred time,
   and available days the planner needs.
5. Run **Subjects → Add subject** — copy the `subject_id` from the response
   into the `subjectId` variable.
6. Run **Exams → Add exam** — attaches an exam date to that subject.
7. Run **Study Planner → Generate timetable** — this is the Smart Planner
   actually building the schedule. The response is the list of sessions it
   created.
8. Copy a `session_id` into the `sessionId` variable, then try **Start
   session** and **Complete session**.
9. Run **Progress → Get progress** and watch the numbers reflect what you
   just did.

## API summary

All routes below (except `/auth/*`) require a header:
`Authorization: Bearer <token>` (the token Register/Login gives you).

| Method | Route | What it does |
|---|---|---|
| POST | `/api/auth/register` | Create an account |
| POST | `/api/auth/login` | Log in, get a token |
| GET/PATCH | `/api/users/me` | View / edit profile & preferences |
| GET/POST | `/api/subjects` | List / add subjects |
| PATCH/DELETE | `/api/subjects/:id` | Edit / delete a subject |
| GET/POST | `/api/exams` | List / add exams |
| PATCH/DELETE | `/api/exams/:id` | Edit / delete an exam |
| POST | `/api/sessions/generate` | Build (or rebuild) the timetable |
| GET/POST | `/api/sessions` | List sessions / add one manually |
| PATCH/DELETE | `/api/sessions/:id` | Edit, reschedule, or delete a session |
| POST | `/api/sessions/:id/start` | Start the study timer |
| POST | `/api/sessions/:id/complete` | Mark complete (also covers "end early") |
| GET | `/api/progress` | Study time, streak, per-subject %, etc. |
| GET/POST | `/api/groups` | List my study groups / create one |
| POST | `/api/groups/join` | Join a group with its join code |
| GET | `/api/groups/:id` | Group detail + member list |
| POST | `/api/groups/:id/leave` | Leave a group |
| DELETE | `/api/groups/:id` | Delete a group (owner only) |
| DELETE | `/api/groups/:id/members/:userId` | Remove a member (owner only) |
| GET/POST | `/api/schools` | List my schools / create one (creator becomes admin) |
| POST | `/api/schools/join` | Join a school with its join code (as a student) |
| GET | `/api/schools/:id` | School detail + member list |
| POST | `/api/schools/:id/leave` | Leave a school |
| DELETE | `/api/schools/:id` | Delete a school (admin only) |
| DELETE | `/api/schools/:id/members/:userId` | Remove a member (admin only) |
| GET/POST | `/api/schools/:id/announcements` | List announcements / post one (admin only) |
| GET/POST | `/api/quizzes` | List my saved quizzes / (see generate below) |
| POST | `/api/quizzes/generate` | Generate a quiz for a subject |
| GET/DELETE | `/api/quizzes/:id` | View / delete a saved quiz |
| POST | `/api/tutor/ask` | Ask the AI tutor a question |
| GET/DELETE | `/api/tutor/messages` | View / clear the tutor conversation |

This whole flow — register through progress — was run end-to-end while
building this to confirm it actually works, not just that it looks right.
The four v2 features below were run end-to-end the same way (see
"v2 features" for details).

## v2 features

Four features were added after the first version shipped: **study
groups**, **school accounts**, an **AI quiz generator**, and an **AI
tutor**. All four are fully working today — the only thing not fully
wired up is a real AI provider, explained below.

- **Study groups** — any user can create a group (`POST /api/groups`),
  which hands back a short `join_code` (like `7F3KQL`) to share with
  friends. Anyone with the code can join (`POST /api/groups/join`). The
  group detail view shows every member and how many sessions they've
  completed, so a group can see who's keeping up. The creator is the
  "owner" and can remove members or delete the group; if an owner
  leaves, ownership passes to whoever joined next.
- **School accounts** — same idea as groups, but with roles: whoever
  creates a school (`POST /api/schools`) becomes its **admin**, and
  everyone who joins with the code becomes a **student**. Only an admin
  can post announcements (`POST /api/schools/:id/announcements`) or
  remove members. An admin can't leave a school full of students unless
  another admin exists first — this stops a school from being left
  without anyone in charge.
- **AI quiz generator** (`POST /api/quizzes/generate`) — pick a subject
  (and optionally a topic), and it builds a multiple-choice quiz with
  answers and explanations, saved so you can come back to it later.
- **AI tutor** (`POST /api/tutor/ask`) — ask a question about a subject
  and get a reply, with the last 20 messages kept as conversation
  history so follow-up questions make sense.

### About the "AI" part

You chose to skip getting an AI provider key for now, so both AI
features work today with a **clearly-labelled placeholder** in place of
a real AI answer — every quiz question and every tutor reply says so
outright, and the response also includes `"ai_connected": false` so an
app built on this API can show a "connect AI" banner if it wants to.
Nothing about generating, saving, listing, or deleting quizzes/messages
is fake — only the actual "write me a good question" / "explain this
well" step is stubbed.

**Turning on the AI features later:** get an API key from an AI
provider — e.g. [Anthropic](https://console.anthropic.com) or
[OpenAI](https://platform.openai.com) both offer one — add it to your
`.env` file as `AI_API_KEY=...`, then open `src/utils/ai_client.py` and
fill in the two `# TODO` spots (`generate_quiz` and `tutor_reply`) with
a real request to that provider. Every controller and the test page
already call those two functions and don't need to change at all.

## Notes on decisions made while building this

- **Zero dependencies was a deliberate choice**, not a shortcut: it means
  nothing can go wrong in a `pip install` step, which matters if this is
  your first time running a backend. The tradeoff is that
  `src/lib/http_kit.py` and `src/utils/crypto_utils.py` are hand-written
  instead of using the well-known, battle-tested `Flask`, `PyJWT`, and
  `bcrypt` packages. They do the same job, but see the section below for
  swapping to the standard packages later.
- **Pause isn't persisted server-side.** The timer's start/pause/resume is
  a frontend concern (it's just a clock); the backend only records when a
  session was *started* and when it was *completed*, with however many
  minutes actually elapsed.
- **Missed sessions** are detected two ways: lazily (any `GET /sessions` or
  `GET /progress` sweeps for overdue ones first) and on a 15-minute timer in
  `server.py`, so a session flips to `missed` even if nobody happens to
  open the app right when it's due.
- **Regenerating the timetable never deletes history** — `POST
  /sessions/generate` only replaces *future* sessions that are still
  `not_started`. Anything already started, completed, or hand-edited is
  left alone.
- **Topics default to "General review"** since there's no topic list in
  the data model yet — the student is meant to edit that field in per
  session.

## Hardening notes (added after the v1/v2 features)

A pass focused purely on making what already exists more solid — no new
features, nothing changes about how you use the API. All of this was
tested (see `README`'s "this whole flow was run end-to-end" note — the
same applies here, plus new checks for each item below).

- **Handles more than one person at once.** The server now uses Python's
  `ThreadingHTTPServer` instead of the plain single-request-at-a-time
  version, so if two members of the same study group (or two students
  in the same school) use the app at the same moment, neither has to
  wait on the other. `src/config/db.py` takes a lock around every
  database read/write so this stays safe with SQLite underneath.
- **A missing or default JWT_SECRET now warns loudly** when you start
  the server — it's easy to forget to change it, and an unchanged
  secret means anyone who saw this code could forge a login token. It
  still starts (so it doesn't break local testing), but set
  `REQUIRE_STRONG_SECRET=1` in `.env` before running this anywhere
  other than your own computer, and it'll refuse to start with a weak
  secret instead of just warning.
- **A second copy of the server won't crash with a wall of red text
  anymore.** If port 4000 (or whatever `PORT` you set) is already in
  use, you get one clear sentence telling you what to do instead of a
  Python traceback.
- **A very large request body is rejected (413) instead of accepted.**
  Nothing in this API legitimately needs more than a few KB per
  request, so anything over 1 MB is turned away before it's read into
  memory.
- **Login and register are rate-limited** — 10 attempts per minute per
  IP address — to slow down anyone trying to guess passwords by brute
  force. A real person mistyping their password a few times will never
  notice this.
- **Tighter input checks:** email addresses are now checked for a
  plausible shape (not just "not empty"), and free-text fields (names,
  subject/exam names, group/school names, announcement text, quiz
  topics, tutor messages) all have a sensible maximum length now, so
  nothing can quietly fill the database with megabytes of junk in one
  field.
- **Two small security response headers** (`X-Content-Type-Options`,
  `X-Frame-Options`) are now sent on every response - standard,
  low-effort protections against a couple of classic browser-based
  attacks.

None of this changes any request or response shape you were already
using — it's entirely about what happens at the edges (bad input, too
much traffic, a missing config value) rather than the normal path.

## Swapping in the standard packages later

When you're running this on your own computer (with normal, unrestricted
internet access — this was built somewhere that couldn't reach PyPI, which
is why it has zero dependencies), you can switch to the well-known version
of each piece without touching the routes or controllers at all:

- `pip install flask` → replace `src/lib/http_kit.py`'s `create_app` /
  `create_router` calls with `Flask(__name__)` / `Blueprint(...)`. Every
  controller already uses `req.params`, `req.body`, `res.status().json()`
  in a Flask-like shape.
- `pip install bcrypt PyJWT` → in `src/utils/crypto_utils.py`, swap the
  scrypt/HMAC functions for `bcrypt.hashpw`/`bcrypt.checkpw` and
  `jwt.encode`/`jwt.decode`.
- `pip install python-dotenv` → replace the two lines at the top of
  `server.py` (`from src.config.env import load_env` / `load_env()`) with
  `from dotenv import load_dotenv; load_dotenv()`.
- For a bigger app, `src/config/db.py`'s `sqlite3` calls translate closely
  to `SQLAlchemy` or `psycopg2` if you move to PostgreSQL later.
