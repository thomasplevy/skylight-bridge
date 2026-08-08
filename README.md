# Keep → Skylight Sync

Scale-to-zero [Fly.io](https://fly.io) Python app that copies unchecked items from Google Keep lists into Skylight lists (`gkeepapi` + `pyskylight`).

Triggered by:

1. **GitHub Actions** — 4× daily cron (+ manual `workflow_dispatch`)
2. **IFTTT / Nest** — “Hey Google, activate sync my lists”

Unofficial APIs on both sides. Personal use only.

```text
Nest / GitHub Actions  →  POST /sync  →  Fly (wakes)
                                      →  Keep (read unchecked)
                                      →  Skylight (add item)
                                      →  Keep (check off item)
                                      →  idle / stop
```

## Keep lists

Create these lists in Google Keep (titles must match, or override via env):

| Keep title   | Env (Skylight list id)     |
|-------------|----------------------------|
| `Groceries` | `SKYLIGHT_LIST_GROCERIES`  |
| `Sam's Club`| `SKYLIGHT_LIST_SAMS`       |
| `Todo`      | `SKYLIGHT_LIST_TODO`       |
| `Home Depot`| `SKYLIGHT_LIST_HOME_DEPOT` |

Set Keep as your Assistant notes provider so Nest can add items:

[Google help: Notes & Lists → Keep](https://support.google.com/assistant/answer/14171370)

Voice examples:

- “Hey Google, add milk to my Groceries list”
- “Hey Google, add paper towels to my Sam's Club list”

Then sync (scheduled or voice) to push into Skylight.

## One-time bootstraps

### Skylight refresh token + list ids

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "git+https://github.com/joshuaswarren/pyskylight"

export SKYLIGHT_EMAIL='you@example.com'
export SKYLIGHT_PASSWORD='…'
skylight login
skylight frames
skylight lists --frame <FRAME_ID>
```

Refresh token: `~/.cache/pyskylight/token.json` → `refresh_token`.

### Google Keep master token

`gkeepapi` needs an Android-style **master token** (treat like a password).

With Docker (from [gkeepapi docs](https://gkeepapi.readthedocs.io/)):

```bash
docker run --rm -it --entrypoint /bin/sh python:3 -c \
  'pip install gpsoauth; python3 -c '\''print(__import__("gpsoauth").exchange_token(input("Email: "), input("OAuth Token: "), input("Android ID: ")))'\'
```

Follow current [gpsoauth](https://github.com/simon-weber/gpsoauth) instructions for obtaining the OAuth token / Android ID.

## Deploy on Fly

```bash
cd sync
fly apps create skylight-keep-sync   # if name free; else edit fly.toml app =
fly volumes create data --region phx --size 1

fly secrets set \
  SYNC_SECRET='long-random-string' \
  GOOGLE_EMAIL='you@gmail.com' \
  GOOGLE_MASTER_TOKEN='…' \
  SKYLIGHT_REFRESH_TOKEN='…' \
  SKYLIGHT_FRAME_ID='…' \
  SKYLIGHT_LIST_GROCERIES='…' \
  SKYLIGHT_LIST_SAMS='…' \
  SKYLIGHT_LIST_TODO='…' \
  SKYLIGHT_LIST_HOME_DEPOT='…'

# Optional Keep title overrides (defaults shown):
# KEEP_LIST_GROCERIES='Groceries'
# KEEP_LIST_SAMS="Sam's Club"
# KEEP_LIST_TODO='Todo'
# KEEP_LIST_HOME_DEPOT='Home Depot'

fly deploy
```

Test:

```bash
curl -X POST "https://skylight-keep-sync.fly.dev/sync" \
  -H "Authorization: Bearer $SYNC_SECRET"
```

`GET /health` does not require auth.

The `/data` volume stores rotated Skylight tokens and a Keep state cache.

## GitHub Actions cron

Repo secrets:

| Secret         | Value                                      |
|----------------|--------------------------------------------|
| `FLY_SYNC_URL` | `https://skylight-keep-sync.fly.dev`       |
| `SYNC_SECRET`  | same as Fly `SYNC_SECRET`                  |

Workflow: [`.github/workflows/sync-lists.yml`](.github/workflows/sync-lists.yml)

- Schedule: `0 2,8,14,20 * * *` (UTC)
- Manual: Actions → **Sync Keep → Skylight** → Run workflow

## IFTTT on-demand voice

1. **If:** Google Assistant → Activate scene → scene name `sync my lists`
2. **Then:** Webhooks → Make a web request
   - URL: `https://skylight-keep-sync.fly.dev/sync`
   - Method: `POST`
   - Headers: `Authorization: Bearer <SYNC_SECRET>`
3. Say: **“Hey Google, activate sync my lists”**

Optional: Google Home Routine with a shorter phrase that runs that scene.

## Local dev

```bash
cd sync
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATA_DIR=./.data
# export the same secrets as Fly…
uvicorn app.main:app --reload --port 8080
```

## Notes

- Sync **checks off** Keep items after a successful Skylight add (does not delete).
- Cold start on Fly can take a few seconds; the HTTP request is held open until sync finishes.
- Both Keep and Skylight private APIs can break without notice.
