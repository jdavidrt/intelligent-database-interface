"""Evaluation harness for docs/EVALUATION_PROTOCOL.md.

Top-level package (not under tests/) because it is imported by both the offline
pytest suite and by standalone CLI scripts, and `pyproject.toml` puts the repo
root on `pythonpath`. Adding `tests/__init__.py` to make `tests.evaluation`
importable would flip pytest's import mode for the whole existing suite, so the
package lives here instead.
"""
