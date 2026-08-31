The app runs after **one** edit to the compose file. The first launch failed because of a real bug in the generated build setup.

## Launch

```bash
cd apps/codex
docker compose up --build -d          # start_command.txt
```

## The failure

The [Dockerfile](../apps/codex/Dockerfile) is multi-stage, and its **final** stage is `test`:

```dockerfile
FROM python:3.12-slim AS runtime
...
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]

FROM runtime AS test
USER root
COPY tests ./tests
RUN pip install ".[test]"
CMD ["pytest"]
```

The compose file declared no build target:

```yaml
  api:
    build:
      context: .
```

Docker defaults to the last stage, so it built the `test` image, whose `CMD ["pytest"]` overrides the runtime `CMD`. The container ran the test suite and exited; `restart: unless-stopped` restarted it, so it sat in a restart loop instead of starting uvicorn. The healthcheck on `/health/live` never passed because the server never came up.

## The fix

One line added to the `api` service's build config in [docker-compose.yml](../apps/codex/docker-compose.yml):

```yaml
  api:
    build:
      context: .
      target: runtime
```

## Commit evidence

The app was generated in `466321f`. Exactly one commit was needed to make it run:

```
$ git show --stat 703b89b -- apps/codex/
703b89b runnable
 apps/codex/docker-compose.yml | 1 +
 1 file changed, 1 insertion(+)

$ git show 703b89b -- apps/codex/docker-compose.yml
@@ -35,6 +35,7 @@ services:
   api:
     build:
       context: .
+      target: runtime
```

The change count for this generated app is therefore **one single-line configuration fix**, and no change to any application source file.
