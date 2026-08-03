FROM python:3.12-slim

WORKDIR /srv

# Pinned, matching the technology baseline the specification fixes.
RUN pip install --no-cache-dir \
      fastapi==0.115.6 \
      "uvicorn[standard]==0.34.0" \
      sqlalchemy==2.0.36 \
      "psycopg[binary]==3.2.3"

COPY app ./app

EXPOSE 8080

# A single worker. Admission control is enforced in-process, so spreading
# requests across worker processes would give each its own independent limit and
# the configured ten would not be the effective one.
#
# Concurrency limits are raised so the server can pick up a burst immediately
# and let admission control decide; the thread limiter is raised in the app's
# lifespan, where the reasoning is recorded.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", \
     "--workers", "1", "--limit-concurrency", "512", "--backlog", "512"]
