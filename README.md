# SPA "Comments" — test assignment

A single-page feedback app: users register, pass a CAPTCHA and leave comments
with infinitely nested cascade replies, images and text files. Built with
**Django + DRF + Vue 3**, plus Junior+ level tooling: **Queue** (Celery),
**Cache** (Redis), **Events** (Django signals + WebSocket), **JWT** (SimpleJWT).

## Features (per the assignment checklist)

- **Comment form** (logged-in users only): Home page (url, optional),
  CAPTCHA `[A-Za-z0-9]+` with an image (required), Text (required), one
  attachment — image or TXT. User Name and E-mail come from the JWT profile,
  so the author cannot be spoofed.
- **Main page**: top-level comments as a sortable list — by User Name, E-mail
  and date, both directions; LIFO by default. Pagination of 25 per page,
  served with just 3 SQL queries per page (COUNT + tops + subtree in one query).
- **Cascade**: infinitely nested replies; the tree is assembled in Python in
  O(n) with no N+1.
- **Files**: a single "📎 Image or TXT" button. JPG/GIF/PNG are downscaled to
  320×240 (Pillow, LANCZOS, proportional) in the background via Celery;
  TXT ≤ 100 KB. Click-to-view with a darkened backdrop: lightbox for images,
  a modal with text + download button for TXT.
- **Preview without reload**: live, via `POST /api/comments/preview/` with a
  debounce (the server returns already-sanitized HTML — raw markup never
  reaches `v-html`). BB-toolbar `[i] [strong] [code] [a]`.
- **Validation, client + server**. XSS: regex+stack check tag balance, `bleach`
  does whitelist escaping. SQL injection: Django ORM everywhere, no raw SQL;
  `?sort=` goes through a field whitelist.
- **WS**: `ws://…/ws/comments/` — a `comment.created` event, the frontend
  refreshes the list live.
- **CAPTCHA**: `django-simple-captcha` (DB table `captcha_captchastore`,
  5-min TTL, one-time — burns on the first attempt): issuance via
  `GET /api/captcha/refresh/` (XHR), image via `GET /api/captcha/image/<key>/`.
  The `[A-Za-z0-9]` alphabet is set through the stock extension point
  `CAPTCHA_CHALLENGE_FUNCT` (`services/captcha.py::alnum_challenge`), no monkeypatch.
- **Auth**: registration `POST /api/register/`, email + password login
  `POST /api/token/`, refresh `POST /api/token/refresh/`, profile `GET /api/me/`.
  The frontend keeps the pair in localStorage, an interceptor attaches Bearer
  and refreshes access on 401. Records are never deleted — there is no DELETE.

## Architecture and decisions made

Stack: **Django 5 + DRF + Channels (daphne)** / **Vue 3 + Vite + TypeScript** /
**PostgreSQL 16** (the only database — in prod and in tests) / **Redis 7**
(cache, Celery broker, WS transport) / **Celery + beat** / **nginx** for the
frontend and `/media/`.

```
backend/
  config/            # settings.py (single file + env), urls, asgi/wsgi, celery.py
  apps/comments/
    models.py        # Comment(MPTTModel): parent FK, MPTT fields, attachments
    serializers.py   # format validation + CAPTCHA + author from JWT (no business logic)
    views.py         # thin list/create/preview + register/token/me
    selectors.py     # read side: sorting, subtree, versioned cache
    services/        # sanitizer, files, captcha adapter, comments (use-case),
                     # tree (O(n) assembly), events (WS event)
    signals.py       # post_save -> broadcast + cache bump + resize enqueue
    tasks.py         # celery: resize_comment_image, cleanup_expired_captchas
    consumers.py + routing.py# WS push
    management/commands/seed_comments.py  # 30 tops (2 pages) + depth-4 trees
frontend/src/
  api/               # client (axios + JWT interceptor), comments, auth
  composables/       # useAuth (singleton), useComments, useCaptcha
  components/        # CommentForm, CommentCard, Pagination, BbToolbar,
                     # CaptchaField, AuthPanel
docs/db_schema.sql   # exact PostgreSQL DDL (taken from sqlmigrate)
```

Why this way and not otherwise:

- **No DDD/repositories/UoW** — overkill for single-entity CRUD. Instead a
  Django-idiomatic slice: Transport (views/serializers) → Services (use-cases)
  → Selectors (reads) → Models (data only). No function longer than ~25 lines;
  every function has a docstring (what it does, Args, Returns, Raises).
- **django-mptt** instead of a plain parent FK + SQL recursion: levels/edges are
  computed on save, a page subtree is a single query, thread order is deterministic.
- **One `file` on the API/service boundary** instead of `image`/`text_file`:
  the frontend has one button, routing by extension happens inside (`is_image()`);
  the DB keeps two columns since they have different `upload_to` and display.
- **Author as a snapshot from JWT**, no FK to User: later email changes never
  rewrite history, and there are no joins.
- **Versioned cache** instead of deleting keys: invalidating the whole list is
  one atomic `INCR`; old keys quietly expire by TTL (5 min). Works identically
  on Redis and locmem.
- **Signals instead of direct calls**: the view only saves; broadcast, cache
  bump and resize enqueue are a `post_save` listener. The socket carries only a
  nudge `{type, id}` — the frontend refetches with the normal request, so there
  is no hand-placing of comments into a sorted list.
- **Resize in the background**: the 201 returns immediately, the worker shrinks
  the file on disk. Locally/in tests — eager mode (`CELERY_EAGER`, default True),
  no worker needed.
- **Tests in one place** — the `backend/apps/comments/tests/` package
  (`test_api/list/mptt/seed/units/sanitizer/ws/cache/tasks/auth` + shared
  `helpers`), a single command with the stock Django runner. No frontend tests
  by design: there is almost no unit-testable logic in the frontend (state + render).

## A note on the frontend

The main focus of this assignment is backend development (JWT, Celery/Redis
queues, WebSockets, DB optimization). To keep the project testable, the Vue.js
client SPA was AI-generated. This provides a functional QA-ready interface out
of the box without shifting focus away from the server-side architecture.

## API

| Method | Path                                      | Access  | Description                                                                  |
| ------ | ----------------------------------------- | ------- | ---------------------------------------------------------------------------- |
| POST   | `/api/register/`                          | guest   | `{user_name, email, password}` → 201 profile                                 |
| POST   | `/api/token/`                             | guest   | `{email, password}` → `{access, refresh}`                                    |
| POST   | `/api/token/refresh/`                     | guest   | `{refresh}` → `{access}`                                                     |
| GET    | `/api/me/`                                | JWT     | own profile                                                                  |
| GET    | `/api/captcha/refresh/`                   | guest*  | `{key, image_url, audio_url}` (*requires `X-Requested-With: XMLHttpRequest`) |
| GET    | `/api/captcha/image/<key>/`               | guest   | PNG image                                                                    |
| GET    | `/api/comments/?sort=-created_at&page=1`  | guest   | tree, 25 tops/page, 5-min cache                                              |
| POST   | `/api/comments/`                          | JWT     | multipart `text`, `file?`, `captcha_*` → 201 `{id}` (author from profile)    |
| POST   | `/api/comments/preview/`                  | JWT     | `{text}` → `{html}`                                                          |
| WS     | `/ws/comments/`                           | guest   | `{"type":"comment.created","id":N}`                                          |
| GET    | `/api/schema/`                            | guest   | OpenAPI YAML (also saved as `docs/openapi.yml`)                              |
| GET    | `/api/docs/`                              | guest   | Swagger UI                                                                   |
| GET    | `/api/redoc/`                             | guest   | ReDoc                                                                        |

Sorting via `?sort=`: `user_name`, `email`, `created_at`, with a `-` prefix for
descending; garbage falls back to LIFO.

## Run with Docker (how to submit)

Requirements: Docker + Docker Compose.

```bash
# 1. Clone and enter the directory
git clone <repo-url> && cd SPA-application

# 2. Bring up the whole stand with one command (builds 3 images, starts 6 services)
docker compose up -d --build

# 3. Wait for healthy statuses (~30s) and load demo data (30 tops, 2 pages)
docker compose exec -T backend python manage.py seed_comments
```

Where everything is after startup:

| Service          | Address               | Purpose                                      |
| ---------------- | --------------------- | -------------------------------------------- |
| frontend (nginx) | http://localhost:8080 | the site itself                              |
| backend (daphne) | http://localhost:8000 | API, WS, `/admin/`                           |
| db (postgres:16) | localhost:5432        | `comments` DB (user/password `comments`)     |
| redis            | localhost:6379        | cache, Celery broker, WS transport           |
| worker           | —                     | Celery worker (image resizing)               |
| beat             | —                     | scheduler (captcha cleanup every 5 min)      |

Useful commands:

```bash
docker compose ps                                                # service statuses
docker compose logs -f backend worker                            # logs
docker compose exec -T backend python manage.py createsuperuser  # admin user
docker compose down                                              # stop (data kept in volumes)
docker compose down -v                                           # stop AND wipe DB/media
```

The `backend` command runs `migrate` on startup, so no manual migrating is needed.

## Run locally (no Docker)

Requirements: Python 3.12+, `uv`, Node 20+, a **running PostgreSQL**
(easiest — `docker compose up -d db`, credentials in `.env.example`).

```bash
# 1. Clone and enter the directory
git clone <repo-url> && cd SPA-application

# 2. Start only Postgres (everything else runs locally)
docker compose up -d db

# 3. Backend
uv sync                                            # creates .venv, installs from uv.lock
uv run python backend/manage.py migrate            # apply migrations
uv run python backend/manage.py seed_comments      # demo data (optional, --count N)
uv run python backend/manage.py runserver          # API at http://localhost:8000

# 4. Frontend (second terminal)
cd frontend && npm install && npm run dev          # site at http://localhost:5173
```

Environment variables live in `.env.example` (defaults match compose:
`comments` DB, `localhost` host, port `5432`). Compose containers already set
the DB/Redis hosts (`db`, `redis`) plus `CELERY_EAGER=False` so resizing goes
through the worker instead of inline. Create a local admin with:
`uv run python backend/manage.py createsuperuser`.

## Tests

All tests live in `backend/apps/comments/tests/` (one package, stock Django
runner) and run **only against PostgreSQL** (the same DBMS as prod) — bring
up the DB first:

```bash
docker compose up -d db
uv run python backend/manage.py test apps.comments
```

Test/prod isolation is enforced by the runner itself: tests execute in a
separate `test_comments` database (Django's `test_` prefix), production data
in `comments` is never touched, and the test database is destroyed
automatically when the run finishes (verified: 50 prod rows intact before
and after a green run).

Covered: API (creation/validation/one-time CAPTCHA), listing/sorting/pagination,
preview, uploads (resize/limits/extensions), MPTT integrity, the seed command,
the sanitizer (XSS cases), WS (broadcast + notify-on-create), cache
(hit/invalidation), Celery tasks + beat schedule, auth
(registration/JWT/me/gates).

## DB schema

`docs/db_schema.sql` — the exact PostgreSQL DDL of both tables
(`comments_comment`, `captcha_captchastore`), taken from
`manage.py sqlmigrate`. Stock Django tables (`auth_user` etc.) are not
described by package migrations and are not included.
