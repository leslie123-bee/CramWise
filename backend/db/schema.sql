-- Student Planner database schema (SQLite)
-- Matches the Database section of the product blueprint, plus the
-- 'missed' session status that the Progress screen needs.

CREATE TABLE IF NOT EXISTS users (
  user_id               TEXT PRIMARY KEY,
  name                  TEXT NOT NULL,
  email                 TEXT NOT NULL UNIQUE,
  password_hash         TEXT NOT NULL,
  profile_picture       TEXT,
  study_goal            TEXT,
  preferred_study_time  TEXT NOT NULL DEFAULT 'evening'
                          CHECK (preferred_study_time IN ('morning','afternoon','evening')),
  -- JSON array of 'mon'..'sun', e.g. ["mon","wed","fri"].
  -- Kept as one field for v1; split into its own table later if per-day
  -- times are ever needed (see the blueprint's Decisions section).
  available_days        TEXT NOT NULL DEFAULT '[]',
  created_at             TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS subjects (
  subject_id   TEXT PRIMARY KEY,
  user_id      TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  subject_name TEXT NOT NULL,
  difficulty   TEXT NOT NULL DEFAULT 'medium' CHECK (difficulty IN ('easy','medium','hard')),
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS exams (
  exam_id    TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  subject_id TEXT NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
  exam_name  TEXT NOT NULL,
  exam_date  TEXT NOT NULL, -- ISO date, YYYY-MM-DD
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id              TEXT PRIMARY KEY,
  user_id                 TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  subject_id              TEXT NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
  topic                   TEXT,
  session_date            TEXT NOT NULL, -- ISO date, YYYY-MM-DD
  start_time              TEXT NOT NULL, -- HH:MM, 24h
  duration_minutes        INTEGER NOT NULL DEFAULT 60,
  actual_duration_minutes INTEGER,
  status                  TEXT NOT NULL DEFAULT 'not_started'
                            CHECK (status IN ('not_started','in_progress','completed','missed')),
  started_at              TEXT,
  completed_at            TEXT,
  created_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_subjects_user      ON subjects(user_id);
CREATE INDEX IF NOT EXISTS idx_exams_user          ON exams(user_id);
CREATE INDEX IF NOT EXISTS idx_exams_subject       ON exams(subject_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user       ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_subject    ON sessions(subject_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_date  ON sessions(user_id, session_date);

-- ---------------------------------------------------------------------
-- v2 "Later" features: study groups, school accounts, AI quiz
-- generator, AI tutor. Added after v1 shipped; see the README's
-- "v2 features" section for how each of these works.
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS study_groups (
  group_id    TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  join_code   TEXT NOT NULL UNIQUE,
  created_by  TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS group_members (
  group_id   TEXT NOT NULL REFERENCES study_groups(group_id) ON DELETE CASCADE,
  user_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  role       TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner','member')),
  joined_at  TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (group_id, user_id)
);

CREATE TABLE IF NOT EXISTS schools (
  school_id   TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  join_code   TEXT NOT NULL UNIQUE,
  created_by  TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS school_members (
  school_id  TEXT NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
  user_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  role       TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('admin','student')),
  joined_at  TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (school_id, user_id)
);

CREATE TABLE IF NOT EXISTS school_announcements (
  announcement_id TEXT PRIMARY KEY,
  school_id       TEXT NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
  posted_by       TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  title           TEXT NOT NULL,
  body            TEXT NOT NULL,
  created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS quizzes (
  quiz_id     TEXT PRIMARY KEY,
  user_id     TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  subject_id  TEXT NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
  topic       TEXT,
  -- JSON array of {question, choices, answer_index, explanation}
  questions   TEXT NOT NULL,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tutor_messages (
  message_id  TEXT PRIMARY KEY,
  user_id     TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  subject_id  TEXT REFERENCES subjects(subject_id) ON DELETE SET NULL,
  role        TEXT NOT NULL CHECK (role IN ('user','assistant')),
  content     TEXT NOT NULL,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_group_members_user     ON group_members(user_id);
CREATE INDEX IF NOT EXISTS idx_school_members_user     ON school_members(user_id);
CREATE INDEX IF NOT EXISTS idx_school_announcements    ON school_announcements(school_id, created_at);
CREATE INDEX IF NOT EXISTS idx_quizzes_user            ON quizzes(user_id);
CREATE INDEX IF NOT EXISTS idx_tutor_messages_user      ON tutor_messages(user_id, created_at);
