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
The settings hierarchy is:
- `config/settings/base.py` — shared base
- `config/settings/container/base.py` — reads secrets from env vars
- `config/settings/container/dev.py` — dev overrides (DEBUG=True, etc.)

See `compose.yml` for the full list of required env vars.

## Environment comparison

| | Claude Code **web** (gVisor) | Claude Code **CLI / IDE** (native) |
|---|---|---|
| PostgreSQL | native service | native service |
| Memcached | Podman container, host networking | Docker container |
| GraceDB app | `runserver` or `docker compose up` | `runserver` or k3d helm deploy |
| Docker daemon | ✔ via Podman socket | ✔ native |
| Overlay filesystem | ✘ vfs only | ✔ |
| k3d / Kubernetes | ✘ (cgroup/iptables missing) | ✔ |

The SessionStart hook detects gVisor automatically and switches mode.

## Running for development (native runserver)
1. PostgreSQL is already running on `127.0.0.1:5432`; user `gracedb`, db
   `gracedb`. Do NOT recreate.
2. Memcached is on `127.0.0.1:11211` (started by SessionStart in gVisor;
   start manually otherwise).
3. Install dependencies: `pip install -r requirements.txt`
4. Set required env vars — copy from `compose.yml` `environment:` block and
   set `DJANGO_DOCKER_MEMCACHED_ADDR=127.0.0.1:11211`.
5. `python manage.py migrate && python manage.py runserver 0.0.0.0:8000`

## Running via Docker Compose (gVisor / web)
The `compose.yml` in the repo root provides postgres + memcached + gracedb as
Podman containers. The Podman socket acts as a Docker-compatible API endpoint.

```bash
docker compose up          # first run builds the image (~10 min)
docker compose up --build  # rebuild after Dockerfile changes
docker compose down -v     # stop and remove volumes
```
App is at `http://localhost:8000`. Admin credentials: `admin` / `admin`.

Note: the image build pulls packages from Debian repos. If any host is
behind the environment allowlist the build will fail at that step.

## Running tests
The repo uses pytest (see `pytest.ini`):
```bash
pytest
```
Run after every change.

## Running on Kubernetes (k3d)

### Environment compatibility
The Claude Code **web** environment runs inside a gVisor sandbox. gVisor does
not expose the kernel interfaces required by container orchestrators:

| Requirement | gVisor status | Effect |
|---|---|---|
| iptables / nftables | unsupported | Docker daemon cannot start; k3d fails |
| overlay filesystem | unsupported | containerd image layers fail |
| cgroup rootfs | not fully exposed | kubelet ContainerManager panics |
| `/dev/kmsg` | non-functional | kubelet cannot open it |

k3d, k3s (direct), and Podman-backed Kubernetes all fail in this environment.
Use the CLI or IDE extension on a native Linux host (kernel ≥ 5.4) instead.

### When k3d IS available (CLI / IDE)
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
The chart and `compose.yml` both use Memcached (not Redis) for caching.
In bare `runserver` mode the `CACHES` config has `ignore_exc: True`, so
missing Memcached degrades gracefully.

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
