# Services

Frontend transport (Day 2):

- `api.ts` — wire types mirroring `backend/app/models/envelope.py`, the NDJSON `streamQuery()` generator over `POST /query`, and REST fetchers for `/session*` and `/db/profile`.

No `ws.ts`: per DAY2_PLAN.md Delta 0, NDJSON streaming is the primary transport; `/ws` stays live on the backend but unwired until a concrete need (e.g. a detached multi-client progress view) appears.
