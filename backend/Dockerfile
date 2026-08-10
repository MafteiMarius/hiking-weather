FROM python:3.12-slim

# Pinned to 3.12 to match CI and the spec, even though local dev runs 3.14
# (DECISIONS 005).

# PYTHONUNBUFFERED: logs reach the host's log stream immediately instead of
# sitting in a block buffer, which matters when debugging a failed boot —
# especially on a free tier with no shell to poke around in.
# PYTHONDONTWRITEBYTECODE: no .pyc files in a layer that is never re-executed.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# No compilers installed on purpose: every runtime dependency (asyncpg,
# pydantic-core, argon2-cffi-bindings) publishes a manylinux wheel for cp312,
# so the ~300 MB gcc/libpq-dev toolchain the first draft carried was dead
# weight. If a future dependency has no wheel, the build fails loudly here —
# add `build-essential` back at that point rather than pre-emptively.

# ── Dependency layer ──────────────────────────────────────────────────────────
# Dependencies change rarely, application code changes every push. Installing
# them in a separate layer means a code-only deploy reuses the cached layer
# instead of re-resolving the whole tree (~2 minutes per deploy).
#
# The stub package exists because `pip install .` reads dependencies from
# pyproject.toml but also insists the package itself be importable — and the
# real source isn't copied yet. The stub satisfies setuptools' discovery, gets
# thrown away, and the real package is installed below with --no-deps.
COPY pyproject.toml ./
RUN mkdir -p app && touch app/__init__.py \
    && pip install --no-cache-dir . \
    && rm -rf app

# ── Application layer ─────────────────────────────────────────────────────────
COPY . .
# The build/ and *.egg-info/ directories setuptools leaves behind are inputs to
# the install, not outputs of it — dropping them keeps the final layer clean.
RUN pip install --no-cache-dir --no-deps . \
    && rm -rf build *.egg-info

# Drop privileges: nothing at runtime writes to the filesystem, so the process
# has no reason to be root.
RUN useradd --create-home --uid 1000 hikecast && chown -R hikecast:hikecast /app
USER hikecast

EXPOSE 8000

# Render (and every other container host) injects $PORT and expects the process
# to bind it; the default keeps `docker run -p 8000:8000` working locally.
# Nothing here is host-specific, which is what makes moving between providers a
# config change rather than a rewrite.
#
# Migrations run on start rather than in a separate release step because
# Render's free tier has no release phase and no shell. Alembic takes a lock,
# so a restart is safe — but a migration failure will (deliberately) stop the
# container from serving a schema it doesn't match.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
