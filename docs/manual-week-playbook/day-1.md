# Day 1 — Foundation and Baseline Capture

## Day target

- Create **6** notes
- No updates/deletes
- Validate buffer read consistency across rounds

## Round 1 (09:00) — Morning capture

Add 3 buffer entries:

1. Energy: baseline appliance load by hour
2. Garden: current watering schedule and weak zones
3. Knowledge workflow: daily note triage friction

Run:

```bash
memory buffer add --content "Energy baseline: evening peak between 19:00-22:00, fridge cycle spikes every 45m." --source "week-sim-day1"
memory buffer add --content "Garden zones A/B dry quickly; current watering 06:00 only may be insufficient." --source "week-sim-day1"
memory buffer add --content "Knowledge triage is slow: inbox tags are inconsistent and backlog grows by end of day." --source "week-sim-day1"
memory buffer list --unprocessed --pretty
```

Checkpoint: confirm 3 new entries are visible.

## Round 2 (13:00) — Midday review + add

Re-read first, then add 2 entries:

4. Project ops: sprint board blocked by unclear ownership
5. Energy: test smart plug scheduling for standby loads

Run:

```bash
memory buffer list --unprocessed --pretty
memory buffer add --content "Project board blockers: unclear owner for deployment checklist and release note approval." --source "week-sim-day1"
memory buffer add --content "Try smart plug schedule to cut standby loads for media cabinet overnight." --source "week-sim-day1"
memory buffer list --unprocessed --pretty
```

Checkpoint: confirm earlier morning entries still present plus 2 new ones.

## Round 3 (17:30) — Afternoon capture

Add 1 entry:

6. Garden alerting: moisture sensor threshold too noisy after rain

Run:

```bash
memory buffer add --content "Moisture alerts are noisy after rainfall; need debounce window before triggering irrigation." --source "week-sim-day1"
memory buffer list --unprocessed --pretty
```

Checkpoint: confirm 6 unprocessed entries for day.

## Round 4 (21:00) — Day-end dreaming

Convert all 6 unprocessed entries into notes.

Tags by topic:

- energy: `energy,home`
- garden: `garden,irrigation`
- knowledge: `knowledge,workflow`
- project ops: `project,delivery`

Create 6 notes and link only within same topic (except 1 bridge link):

- Bridge link: knowledge triage note → project blockers note (`related_to` via `workflow` impact)

Process all buffer entries used for conversion.

End checks:

```bash
memory notes list --limit 20 --pretty
memory buffer list --unprocessed --pretty
memory admin stats --pretty
```

Expected:

- total notes: 6
- unprocessed buffer: 0
