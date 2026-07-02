# Agents (Day 2 target)

One module per agent, each a pure-ish function over the typed Pydantic envelope:
`context_manager.py`, `query_understanding.py`, `clarification.py`,
`sql_generator.py`, `verification.py`, `visualization.py`.
Session Manager is cross-cutting and lives under `services/memory/`.
