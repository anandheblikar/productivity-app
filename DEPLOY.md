# Deploy as a free website (Render + Neon)

This hosts the app for free, reachable from your phone, with your data saved
in a cloud Postgres database so it persists. No credit card needed.

- **App** → Render (free web service, automatic HTTPS, sleeps when idle)
- **Data** → Neon (free Postgres, doesn't expire)

> Heads-up: it's a **public** URL protected only by your password — so pick a
> strong `APP_PASSWORD`. Uploaded audio/video recordings are **not** saved on
> the free tier (the database content is). First visit after idle takes
> ~30–60s to wake up.

---

## 1. Put the code on GitHub

It already is — on the `build-v1` branch of your `productivity-app` repo.
(If you want, merge it into `main` first; Render can deploy either branch.)

## 2. Create the database (Neon)

1. Go to <https://neon.tech> → **Sign up** (use "Continue with GitHub" — no card).
2. Create a project (any name, e.g. `tonight`). Accept the defaults.
3. On the project dashboard, find **Connection string** and copy it. It looks
   like:
   `postgresql://user:password@ep-xxxx.region.aws.neon.tech/dbname?sslmode=require`
4. Keep this handy — it's your `DATABASE_URL` in the next step.

## 3. Create the web service (Render)

1. Go to <https://render.com> → **Sign up** with GitHub (no card).
2. **New +** → **Web Service** → connect your `productivity-app` repo.
3. Settings:
   - **Branch:** `build-v1` (or `main` if you merged)
   - **Runtime:** Docker (it auto-detects the `Dockerfile`)
   - **Instance type:** Free
4. Add **Environment variables** (Advanced → Add Environment Variable):

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | the Neon connection string from step 2 |
   | `APP_PASSWORD` | a strong password you'll type to sign in |
   | `APP_SECRET` | a long random string — generate with the command below |
   | `APP_HTTPS_ONLY` | `1` |

   Generate `APP_SECRET` locally:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
5. **Create Web Service.** Render builds the image and deploys it (first build
   takes a few minutes). When it's live you'll get a URL like
   `https://tonight-xxxx.onrender.com`.

## 4. Use it

Open the Render URL on your phone, sign in with `APP_PASSWORD`, and add it to
your home screen if you like. The database starts empty — add your items
fresh (your local data stays on your Mac; it isn't copied up automatically).

---

## Notes

- **Updating the app:** push to the deployed branch and Render redeploys
  automatically. Your data is safe in Neon across redeploys.
- **Backups:** Neon keeps your data; you can also branch/snapshot it from the
  Neon dashboard.
- **Moving your existing items up (optional):** your local items live in
  `productivity.db`. They can be copied into Neon later with a small script —
  ask and I'll write one. By default you start clean in the cloud.
- **Recordings:** to persist uploaded audio/video in the cloud, we'd add
  object storage (e.g. S3/Cloudflare R2) — a later step.
