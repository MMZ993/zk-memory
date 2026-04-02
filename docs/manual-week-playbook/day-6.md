# Day 6 — Stress Day and Cross-checks

## Day target

- Create **7** notes
- Update **2** notes
- No deletes

## Round 1 (09:00) — Morning capture

Add 3 buffer entries:

1. Project ops: pre-release freeze criteria
2. Garden: soak-cycle timing for clay soil
3. Energy: EV charging schedule conflict with HVAC peak

Read unprocessed list.

## Round 2 (13:00) — Midday review + add

Re-read then add 2 entries:

4. Knowledge: confidence score field for uncertain notes
5. Project ops: incident owner handoff protocol

Re-read unprocessed list.

## Round 3 (17:30) — Afternoon capture

Add 2 entries:

6. Garden alerts: sensor offline fallback behavior
7. Energy dashboard: compare week-over-week load curves

Read unprocessed list and verify all entries still visible.

## Round 4 (21:00) — Day-end dreaming

Create 7 notes from buffer.

Planned updates (2):

1. Update Day 4 battery threshold note with EV/HVAC conflict logic.
2. Update Day 5 digest template note with confidence score field.

Link policy:

- dense links inside project ops and energy
- garden links mostly within garden
- one bridge only: incident handoff protocol ↔ sensor offline fallback

Process all consumed buffer entries.

End checks:

```bash
memory notes list --limit 100 --pretty
memory notes search "freeze criteria" --mode hybrid --pretty
memory notes search "week-over-week load" --mode semantic --pretty
memory buffer list --unprocessed --pretty
```

Expected running total:

- notes: 35
- unprocessed buffer: 0
