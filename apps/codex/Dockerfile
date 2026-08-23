FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/oms

RUN addgroup --system oms && adduser --system --ingroup oms oms

COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY create_apis.json openapi.yaml nfr-trace.json start_command.txt ./
RUN pip install --upgrade pip && pip install .

USER oms
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]

FROM runtime AS test

USER root
COPY tests ./tests
RUN pip install ".[test]"
CMD ["pytest"]
