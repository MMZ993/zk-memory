# Day 3 — Pruning and Signal Cleanup

## Day target

- Create **5** notes
- Update **1** note
- Delete **1** outdated note

## Round 1 (09:00) — Morning capture

Add 2 buffer entries:

1. Garden: rain-skip rule should include 24h forecast
2. Project ops: standup notes need action owner field

Read unprocessed list.

## Round 2 (13:00) — Midday review + add

Re-read then add 2 entries:

3. Energy: identify top standby offenders by smart plug telemetry
4. Knowledge: weekly review should auto-group by topic tag

Re-read to confirm all 4 are visible.

## Round 3 (17:30) — Afternoon capture

Add 1 entry:

5. Project ops: release readiness score formula draft

Read unprocessed list again.

## Round 4 (21:00) — Day-end dreaming

Create 5 notes from today’s buffer.

Planned update (1):

- Update Day 2 valve latency note with measured response threshold and mitigation note.

Planned delete (1):

- Delete one low-value Day 1 project blocker note that was superseded by the new checklist + readiness score notes.

Link policy:

- dense links inside garden and project topics
- one bridge: energy telemetry note ↔ project readiness score (shared dashboard dependency)

Process all consumed buffer entries.

End checks:

```bash
memory notes list --limit 40 --pretty
memory notes search "readiness score" --mode semantic --pretty
memory buffer list --unprocessed --pretty
```

Expected running total:

- notes: 16
- unprocessed buffer: 0
