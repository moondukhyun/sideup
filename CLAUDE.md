# CLAUDE.md

Guidance for Claude Code (and other AI assistants) working in this repository.

## What this repo is

`sideup` is a minimal serverless proxy to the Anthropic Messages API, structured
for zero-config deployment on Vercel. There is no build system, no
`package.json`, and no front-end framework — just two files.

## Repository structure

```
.
├── index.html       # See "Known issue" below — currently NOT valid HTML
└── api/
    └── claude.js     # Vercel serverless function (Node, ESM)
```

### `api/claude.js`

A Vercel API route (`/api/claude`) that:
- Accepts `POST` (and `OPTIONS` for CORS preflight) requests.
- Sets permissive CORS headers (`Access-Control-Allow-Origin: *`).
- Forwards the request body (`messages`, `max_tokens`) to
  `https://api.anthropic.com/v1/messages`.
- Reads the Anthropic API key from the `ANTHROPIC_API_KEY` environment
  variable — this must be set in the Vercel project settings (or a local
  `.env`/`vercel env` for local dev). It is never present in source.
- Hardcodes the model to `claude-haiku-4-5-20251001` and the API version
  header to `2023-06-01`.
- Returns the raw Anthropic response JSON as-is, or a `{ error: { message } }`
  payload with a 500 status on failure.

This is the only piece of application logic in the repo. Any change to
request/response shape, model selection, or auth should happen here.

### `index.html` — known issue

`index.html` currently contains an exact byte-for-byte copy of
`api/claude.js`'s JavaScript source, not HTML markup. This is almost
certainly an upload/copy-paste mistake rather than intentional. There is no
working front-end page in the repo yet.

If asked to add or fix the front end, treat `index.html` as needing to be
rewritten as a real HTML page (e.g., a simple chat UI that `POST`s to
`/api/claude`) rather than assuming the current content is meaningful.
Don't assume it's correct just because it's committed.

## Development workflow

There is no `package.json`, lockfile, or build step. Deployment relies on
Vercel's zero-config detection of the `api/` directory as serverless
functions.

- **Local dev**: run `vercel dev` (requires the Vercel CLI) from the repo
  root to serve `index.html` and `api/claude.js` together with the same
  routing Vercel uses in production.
- **Environment variables**: `ANTHROPIC_API_KEY` must be set (via
  `vercel env` or a local `.env` file picked up by `vercel dev`). Without it,
  `api/claude.js` will call Anthropic with an undefined key and get an auth
  error.
- **Deployment**: pushing to the connected branch / `vercel deploy` ships
  both files as-is; there's no compilation or bundling step to run first.
- **Testing**: there is no test suite. Verify changes to `api/claude.js` by
  running `vercel dev` and `curl`-ing `POST /api/claude` with a sample
  `messages` array, or by exercising it from the front end in a browser.

## Conventions to follow

- Keep CORS headers (`Access-Control-Allow-Origin`, `-Methods`, `-Headers`)
  consistent with the existing pattern in `api/claude.js` if adding new API
  routes under `api/`.
- Always read secrets (API keys) from `process.env` — never hardcode them.
- Match the existing error-handling shape: catch errors and return
  `res.status(500).json({ error: { message: e.message } })`.
- This is a tiny, single-purpose project — avoid introducing a build
  toolchain, framework, or dependencies unless the task explicitly requires
  it. Keep additions as plain, dependency-free JS/HTML consistent with the
  current files.
