# GraceDB Server — Notes for Claude Code

## What this is
GraceDB is a Django application that tracks gravitational-wave candidate events
for the LIGO / Virgo / KAGRA collaboration. It uses PostgreSQL for storage and
is normally deployed to Kubernetes via the chart in the sibling repo,
`gracedb-helm-charts`, which the SessionStart hook checks out to
`../gracedb-helm-charts`.

## Ground truth first
Before doing anything else, run `.claude/scripts/doctor.sh` and read its output. It
reports versions of all tools and whether the Postgres / k3d stack is reachable.
Don't trust any other assumption in this file if `doctor.sh` disagrees.

## Django settings
The correct settings module for container-based dev is:
```
DJANGO_SETTINGS_MODULE=config.settings.container.dev
```
This is already set in the environment. The settings hierarchy is:
- `config/settings/base.py` — shared base
- `config/settings/container/base.py` — container-specific base
- `config/settings/container/dev.py` — dev overrides (DEBUG=True, etc.)

## Running for development without Kubernetes
1. PostgreSQL 16 is already running on localhost:5432; user `gracedb`, db
   `gracedb`. Do NOT recreate.
2. `pip install -r requirements.txt`
3. `python manage.py migrate`
4. `DJANGO_SUPERUSER_PASSWORD=admin python manage.py createsuperuser \
      --username admin --email admin@example.com --noinput`
5. `python manage.py runserver 0.0.0.0:8000`

## Running tests
The repo uses pytest (see `pytest.ini`):
```bash
pytest
```
Run after every change.

## Running on Kubernetes (k3d)
1. A k3d cluster named `$K3D_CLUSTER_NAME` is created by the SessionStart hook.
   Kubeconfig is at `$KUBECONFIG`.
2. Build the server image: `docker build -t gracedb-server:dev .`
3. Import into k3d: `k3d image import gracedb-server:dev -c $K3D_CLUSTER_NAME`
4. Follow `../gracedb-helm-charts/CLAUDE.md` for the `helm install` step.
   The chart lives in `../gracedb-helm-charts/gracedb/`.

## Auth in dev
Shibboleth and X.509 client-cert auth are production features. The helm chart
disables Shibboleth when `sandboxed.enabled: true` (set in `values-k3d.yaml`).
For bare Django dev (`runserver`), verify that `SKIP_SHIBBOLETH=1` is honoured
by grepping the codebase — if not, ask before disabling auth globally.

## Memcached
The chart uses Memcached (not Redis) for caching. In bare `runserver` mode the
cache backend falls back to local-memory and Memcached is not required.

## Conventions

### Branch strategy
This repo is mirrored one-way from git.ligo.org. Mirror pushes overwrite any
branch that also exists in the upstream GitLab repo. The only branches safe
from overwrite are those that do not exist upstream.

All Claude work **must** stay on branches prefixed with `claude/`. These
branches are not present in the upstream GitLab repo and will never be
clobbered by a mirror push.

- **Never push to, or open PRs targeting, any branch without a `claude/` prefix.**
- Feature branches follow the pattern `claude/<workspace>`, where `<workspace>`
  describes the task (e.g. `claude/fix-event-search`).
- **At the start of each session, ask the user what workspace name to use.**
  Claude will then work on `claude/<workspace>` for that session.
- Completed feature branches are merged into a `claude/` integration branch
  agreed with the maintainer (e.g. `claude/initial_claude_setup`). The
  maintainer cherry-picks from there into the upstream GitLab repo.

### Other conventions
- Don't modify `docker/apache2.conf` or `supervisord.conf` unless asked.
- Keep commits small and descriptive — they will be cherry-picked to GitLab.
