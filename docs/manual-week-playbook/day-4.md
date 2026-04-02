# Day 4 — Midweek Expansion

## Day target

- Create **7** notes
- Update **2** notes
- No deletes

## Round 1 (09:00) — Morning capture

Add 3 buffer entries:

1. Energy: weekend pre-cooling strategy for high tariff window
2. Garden: detect clogged dripper from flow mismatch
3. Knowledge: define archive policy for stale notes

Read unprocessed list.

## Round 2 (13:00) — Midday review + add

Re-read then add 2 entries:

4. Project ops: incident timeline template
5. Energy: battery discharge threshold tuning

Re-read list to verify cumulative entries.

## Round 3 (17:30) — Afternoon capture

Add 2 entries:

6. Garden: map sensor battery replacement cadence
7. Project ops: dependency risk labels for sprint board

Read unprocessed list.

## Round 4 (21:00) — Day-end dreaming

Create 7 notes from buffer.

Planned updates (2):

1. Update Day 2 release checklist note with incident timeline cross-reference.
2. Update Day 1 energy baseline note to include pre-cooling and battery-threshold assumptions.

Link policy:

- strong energy cluster and strong garden cluster
- project ops notes linked to each other
- one cross-topic bridge: archive policy note ↔ dependency risk labels note

Process all consumed buffer entries.

End checks:

```bash
memory notes list --limit 60 --pretty
memory notes search "pre-cooling strategy" --mode hybrid --pretty
memory notes links graph <any-day4-energy-note-id> --depth 2 --pretty
memory buffer list --unprocessed --pretty
```

Expected running total:

- notes: 23
- unprocessed buffer: 0
