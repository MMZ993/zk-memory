# Day 7 — Wrap-up, Cleanup, and Final Validation

## Day target

- Create **8** notes
- Update **2** notes
- Delete **1** note
- End with stable, searchable week corpus

## Round 1 (09:00) — Morning capture

Add 3 buffer entries:

1. Weekly energy summary and next-week experiment list
2. Garden weekly moisture variance summary
3. Project ops weekly bottleneck summary

Read unprocessed list.

## Round 2 (13:00) — Midday review + add

Re-read then add 3 entries:

4. Knowledge: "decision log" note format
5. Energy: anomaly threshold tuning notes
6. Project ops: release readiness KPI definitions

Re-read unprocessed list and validate cumulative visibility.

## Round 3 (17:30) — Afternoon capture

Add 2 entries:

7. Garden: irrigation window shift due to weather forecast
8. Knowledge: archive candidates list for next sprint

Read unprocessed list.

## Round 4 (21:00) — Day-end dreaming

Create 8 notes from buffer.

Planned updates (2):

1. Update Day 6 freeze criteria note with final KPI thresholds.
2. Update Day 3 standby offenders note with week-over-week summary outcomes.

Planned delete (1):

- Delete one obsolete intermediate KPI draft note replaced by the final KPI definitions note.

Link policy:

- keep cluster density high inside each topic
- allow up to 2 bridge links max on final day:
  - weekly energy summary ↔ release readiness KPI definitions
  - decision log format ↔ weekly bottleneck summary

Process all consumed buffer entries.

## Final week validation checklist

Run:

```bash
memory admin stats --pretty
memory notes list --limit 200 --pretty
memory buffer list --unprocessed --pretty

memory notes search "weekly energy summary" --mode semantic --pretty
memory notes search "release readiness KPI" --mode keyword --pretty
memory notes search "irrigation window shift" --mode hybrid --pretty
```

Confirm:

- total notes is in target range (planned: 42)
- unprocessed buffer is 0
- all 4 topics are represented
- semantic/keyword/hybrid searches return expected recent notes
