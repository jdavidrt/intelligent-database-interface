# Benchmarks

Corpora and results for the evaluation protocol in `docs/EVALUATION_PROTOCOL.md`.
The protocol is the authority; this file only says where things live.

## `corpora/` — the four frozen manifests

225 items, one JSON object per line, schema in §2.2.

| File | Items | Stratification | Threshold (Ch1 §1.3) |
|---|---|---|---|
| `spider_style.jsonl` | 60 | 24 easy / 24 medium / 9 hard / 3 extra | 75% min, 85% target |
| `bird_style.jsonl` | 60 | 30 simple / 21 moderate / 9 challenging | 50% min, 60% target |
| `soundwave_30.jsonl` | 30 | 5 Easy / 5 Medium / 7 Hard / 13 Extra Hard | diagnostic, no threshold |
| `idi_exec_75.jsonl` | 75 | 15 low / 30 medium / 30 high, 8 fixed categories | 80% min, 90% target |

All four execute against **SoundWave** — it is the only database in the repo with
data, and §3.1 derives ground truth by executing `reference_sql` rather than by
storing it. 220 of the 225 items carry reference SQL; the 5 that do not are
IDI-EXEC-75's Deliberate Ambiguity items, which §3.6 scores on whether the
pipeline asks for clarification instead of guessing.

**Ground truth is not in these files, deliberately.** It is whatever
`reference_sql` returns against the seeded database under
`IDI_FREEZE_NOW=2026-07-17T12:00:00`. A run without that variable set is void.

**The `evidence` field is never fed to the pipeline** (decided 2026-07-21). In BIRD,
evidence is handed to the model at inference time; here it is corpus metadata only —
documentation of which domain fact an item depends on, used when reading results.
IDI's equivalent of evidence is its own Context Manager: the per-database survey
(`databases/<db>/NN_<db>_survey.json`) feeds the glossary, coded values and
source-of-truth notes into the prompt. Passing the corpus's evidence strings in
alongside would measure a system IDI is not — the whole didactic claim is that the
system supplies domain context itself, so an item the model gets wrong for want of
domain knowledge is a finding about the Context Manager, not a handicap to correct
for. This is a methodology choice, not a protocol change; §2.2 defines the field and
never says to pass it.

## Regenerating and checking

```bash
python -m evaluation.validate              # conformance report, non-zero exit if broken
pytest tests/test_corpora.py               # the same invariants, pinned as tests
```

The manifests are build artifacts. Edit the builder, not the JSONL:

```bash
python -m evaluation.transcribe_soundwave          # soundwave_30, parsed from the syllabus
python -m evaluation.authoring.build_spider_style  # refuses to write on a tier mismatch
python -m evaluation.authoring.build_bird_style
python -m evaluation.authoring.build_idi_exec_75
```

Each builder recomputes every item's difficulty from its SQL via
`evaluation/hardness.py` (a port of Spider's `eval_hardness`) and **refuses to
write the manifest** if a computed tier disagrees with the intended one. §2.1
requires such an item to be re-authored, never relabelled, so there is no flag to
override this.

## Freeze discipline

§0.2 governs. Once a scored run exists: fixing a demonstrably wrong reference
query is allowed and must be logged in §11; adding or removing an item, or
changing a threshold, is not. Two corrections are already logged there — Q22's
reference SQL, and BIRD-036/040, both caught before any run.

## Scored runs

```bash
python run_benchmarks.py                       # menu + live progress — the whole command
python run_benchmarks.py --profile 30m         # unattended preset
python run_benchmarks.py --no-autostart        # require a backend you manage yourself

# without the launcher, the backend must already be running with the frozen
# clock and greedy decoding:
#   IDI_FREEZE_NOW=2026-07-17T12:00:00 IDI_GREEDY=1 python start.py
python -m evaluation.run                       # all 225 items, no menu
python -m evaluation.run --corpus soundwave_30 # one corpus
python -m evaluation.run --total 30            # deterministic proportional subset
```

`run_benchmarks.py` starts llama.cpp and the backend itself if they are not
already up, setting `IDI_FREEZE_NOW` and `IDI_GREEDY` — the two variables whose
absence silently voids a run (§1.1, §1.3). Servers it started are stopped when
the run ends; servers already running are adopted and left alone, including on
Ctrl-C and including when it loses a port race.

**GPU.** llama.cpp is pinned to the discrete GPU by `start.py:pick_gpu_device()`.
This matters more than it sounds: the Vulkan build lists the Intel iGPU first,
so every run before 2026-07-21 offloaded there at 8.6 tok/s instead of 44.6 on
the GTX 1650. The run header now records `vram_used_mb`, and a run labelled
`gpu` whose VRAM use is too low for an offloaded model gets a caveat saying its
latency and tokens/sec are not a GPU-profile result.

### Presets

`run_benchmarks.py` (and `python -m evaluation.run --profile`) offers four
budgets, defined in `evaluation/plan.py`:

| Preset | Items | Tier rule | Estimate |
|---|---|---|---|
| `30m` | 20 | easy-weighted, ~50/30/20 | ~29 min |
| `1h` | 41 | authored stratification | ~1 h |
| `3h` | 123 | authored stratification | ~3 h |
| `full` | 225 | every item | ~5 h 30 min |

The counts are **fixed constants**, sized once against the 87.6 s/item end-to-end
p50 measured by the 2026-07-21 pilot. A preset that resized itself from the
latest measurement would make two runs of the same name incomparable, so the
menu instead shows a live estimate from the newest report on disk while the
count stays put.

**Only `full` is reportable as a §3 corpus EX.** The other three are pilots, and
`30m` is additionally easy-weighted — it deliberately over-samples the easy tier
to get a signal in half an hour, which inflates EX by construction. The header
and the Markdown report say so in their caveats, and `reportable` is `false`.

Selection is stratified three ways — proportionally across corpora, then across
difficulty tiers, then a **manifest-order prefix** within each stratum — so the
planner decides *how many* easy items run, never *which*. §3.6's clarify items
are stratified separately with a floor of one, because all five sit at the tail
of `idi_exec_75` and a plain tier-prefix otherwise left that scoring path
untested even at 190 of 225 items. `tests/test_eval_plan.py` pins all of this
offline.

`evaluation/run.py` feeds each item's `nl` through `POST /query`, scores the
result with `evaluation/scoring.py` (§3.2/§3.3) and writes
`eval_YYYY-MM-DD.{json,md}` — EX per corpus, broken down by category, difficulty
tier and EC tag, plus the pipeline-outcome and verdict distributions.

Two properties are worth knowing before reading a report:

- **The harness refuses to write a void run.** §1.1's frozen clock lives in the
  backend process, so the check reads `GET /health` rather than the harness's
  own environment — a client verifying its own env would prove nothing about
  the process that generated the SQL. `/health` also reports whether greedy
  decoding (§1.3) is active; a non-greedy or partial run is written but marked
  `reportable: false` with the reason in the header.
- **Subsets are chosen before the first query is sent.** Both `--total N` and
  the presets take a manifest-order prefix of each stratum, allocated
  proportionally, and record the rule and the achieved difficulty mix in the
  header. Picking which items to report after seeing the scores is the post-hoc
  tuning §0 exists to prevent.

`eval_2026-07-14.{json,md}` predates this protocol (it is `tests/evaluate.py`'s
8-probe output) and is not a protocol-conformant scored run.
