# Stores

Zustand stores (Day 2):

- `queryStore.ts` — chat messages (incl. the `Message` type), `isWaiting`, the `send()` stream loop, `stop()`, and `loadFromSession()`.
- `progressStore.ts` — live per-agent pipeline steps; merges events per agent so the adapter name (from `payload.adapter`) survives later status updates.
- `sessionStore.ts` — active session id (multi-turn continuity) + session list.
- `dbProfileStore.ts` — lazily fetched `DBProfile` (404 until the first query runs).
