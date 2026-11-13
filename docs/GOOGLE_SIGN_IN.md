# Setting up Sign in with Google

The code is ready; Google only needs to know the app. Until both variables below are set, the API reports `{"google": false}` on `/api/v1/auth/providers` and the app hides the button.

1. Open [Google Cloud Console](https://console.cloud.google.com/) and create (or pick) a project.
2. **APIs & Services → OAuth consent screen**: choose *External*, fill in the app name and your email, and add the scopes `openid`, `email` and `profile`. While the app is in *Testing*, add the Google accounts that may sign in as test users.
3. **APIs & Services → Credentials → Create credentials → OAuth client ID**, type *Web application*. Under **Authorized redirect URIs** add the callback of every place the app runs, always on the app's own origin (which proxies `/api` to the API, so the session cookie is first-party):
   - `http://localhost:4200/api/v1/auth/google/callback` (Angular dev server)
   - `http://localhost:8080/api/v1/auth/google/callback` (Docker Compose)
4. Copy the client ID and secret:
   - dev server and local API: into `backend/.env` as `GOOGLE_CLIENT_ID=…` and `GOOGLE_CLIENT_SECRET=…`;
   - Docker Compose: export them in your shell (or a root `.env` next to `deploy/docker-compose.yml`) before `docker compose up`; Compose passes them to the API.
5. Restart the API. The sign-in page now shows **Continue with Google**.

The redirect URI is built from `FRONTEND_URL` (`{FRONTEND_URL}/api/v1/auth/google/callback`), so it must match one of the URIs registered in step 3 exactly.
