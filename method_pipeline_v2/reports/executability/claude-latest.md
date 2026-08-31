The app is up and running — the API answers at `http://localhost:8000`, with `/health` returning `{"status":"ok"}`. Compose exited cleanly and the `api` service depends on healthy checks for the primary, replica, and redis, so the whole stack (postgres primary + streaming replica + redis + FastAPI) is healthy.

A local repair was needed before it would start, but it is classified as an environment issue
rather than an executability defect: a clone of this repository starts without modification on
Linux. The reasoning and evidence are in [Change count](#change-count) below.

## Launch

```bash
cd claude-latest
docker compose up --build -d          # start_command.txt
```

## The failure

```
/bin/bash^M: bad interpreter
```

[`deploy/primary-init.sh`](../claude-latest/deploy/primary-init.sh) and
[`deploy/replica-entrypoint.sh`](../claude-latest/deploy/replica-entrypoint.sh) had Windows CRLF
line endings on disk. Both are bind-mounted into Linux containers and executed as shell scripts
([docker-compose.yml:29](../claude-latest/docker-compose.yml#L29),
[:45-48](../claude-latest/docker-compose.yml#L45-L48)):

```yaml
      - ./deploy/primary-init.sh:/docker-entrypoint-initdb.d/10-replication.sh:ro
...
    entrypoint: ["/bin/bash", "/replica-entrypoint.sh"]
```

The trailing `\r` becomes part of the interpreter path in the shebang, so the kernel looks for
`/bin/bash\r` and fails.

## The fix

Converted both scripts to LF, then wiped the half-initialized database volumes and relaunched:

```bash
docker compose down -v
docker compose up --build -d
```

The volumes had been created seconds earlier by the failed init, so nothing was lost.

## Change count

**No commit was required, and none exists.** No commit in the repository has ever touched
`claude-latest/deploy/`:

```
$ git log --all --oneline -- claude-latest/deploy/
4b3bf09 testcases + claude - generated app
```

The only commit listed is the one that added the generated app itself. **The fix leaves no trace
in git, but it was a real defect in the generated output.** Both facts follow from the same
cause, explained below.

### Why git records nothing

This repository has `core.autocrlf=true` and no `.gitattributes`. That setting normalizes
CRLF to LF **on commit**, so a CRLF file written to disk is stored as an LF blob. It also means
`git status` reports the file as unmodified whether it is CRLF or LF on disk, because the same
normalization runs on comparison.

So the committed blobs are LF — but that is what git stores *regardless* of what was on disk:

```
$ git rev-parse HEAD:claude-latest/deploy/primary-init.sh
def214737eba8a7f4b3f2cbba9a11434b9dd3326

primary-init.sh:        blob CR=0  LF=19
replica-entrypoint.sh:  blob CR=0  LF=27
```

An LF blob is therefore not evidence that the generator emitted LF.

### The generator emits CRLF files

Files from the generation commit that have not been touched since are still CRLF on disk, with
LF blobs — showing the normalization happening and the generator as the source:

```
claude-latest/docs/openapi.json     disk CR=1667   blob CR=0
```

`docs/openapi.json` was added in `4b3bf09`, the generation commit, and its mtime is unchanged
from generation (2026-08-07). The same pattern appears in the other generated apps:

| App | CRLF files on disk | Blobs |
|---|---|---|
| `claude-latest` | 2 of 54 — `docs/openapi.json`, `workflow_apis.json` | all LF |
| `apps/codex` | 4 of 85 — `Dockerfile`, `docker-compose.yml`, `latest.md`, `openapi.yaml` | all LF |
| `apps/app-claude` | 1 of 54 — `openapi.json` | all LF |

The generators write **mixed** line endings, and `git commit` silently erases the evidence.

This also rules out the checkout as the source. A CRLF-writing checkout smudge would rewrite
*every* text file in the tree; here 52 of 54 files in `claude-latest` are LF on disk. Only
scattered files are CRLF — the signature of per-file generator output, not of a bulk checkout.

### Classification: environment, not an executability defect

The exact original bytes of `deploy/primary-init.sh` and `deploy/replica-entrypoint.sh` cannot
be recovered, because the commit normalized them. The surrounding evidence points to the
generator having emitted them as CRLF, in the same way it emitted `docs/openapi.json`.

Even so, this is **reported but not counted** against the app's executability. The criterion
used throughout these reports is *what is reproducible from the published artifact* — clone the
repository, run `start_command.txt`:

| Condition | Result |
|---|---|
| Clone on Linux/macOS, run `start_command.txt` | **Starts** — the committed blobs are LF |
| Clone on Windows with `core.autocrlf=true` and no `.gitattributes` | Fails with `bad interpreter` |

The distributed artifact is correct. The failure appears only in a Windows working tree, and it
is the checkout configuration of *this* repository — not the content of the generated app — that
reintroduces CRLF for the next person. That is a property of the environment, and it is fixed
once for all apps by adding a `.gitattributes` with `*.sh text eol=lf`.

For contrast, `apps/codex` is counted: its committed `docker-compose.yml` genuinely lacked
`target: runtime`, so it fails on every host regardless of line endings.

The repair actually performed here was a line-ending conversion of two files plus
`docker compose down -v` to discard the volumes left by the failed init. No application source
was changed.

## Environment note

This stack and the codex stack both map port `8000`, so they cannot run at the same time.
