# Week Simulation Playbook (Manual)

## Goal

Run a 7-day manual simulation that stresses:

- buffer write/read behavior across multiple rounds in the same day
- day-end buffer-to-note consolidation ("dreaming")
- note lifecycle operations (create, update, delete)
- mostly intra-topic links with limited cross-topic links

Target final state: **35–50 notes**.

Planned final state: **42 notes**.

## Topics

Use 4 cross-related but mostly separate topics:

1. **Home Energy Optimization**
2. **Smart Garden Irrigation**
3. **Personal Knowledge Workflow**
4. **Project Delivery Ops**

Connection policy:

- strong linking inside each topic
- only 1–2 cross-topic links/day max
- preferred cross-topic bridge tags: `alerts`, `scheduling`, `dashboards`

## Daily cadence template

Each day has 4 rounds:

1. **Morning capture (09:00)**
2. **Midday review + add (13:00)**
3. **Afternoon capture (17:30)**
4. **Day-end dreaming (21:00)**

Buffer validation requirement each day:

- read after morning writes
- write more entries
- read again and verify both early and late entries are returned

Day-end requirement each day:

- convert unprocessed buffer notes into 5–8 permanent notes
- link notes mostly inside same topic
- mark corresponding buffer items as processed

## Commands baseline

Set env once:

```bash
export MEMORY_API_URL=http://localhost:8001
```

Common commands:

```bash
memory buffer add --content "..." --source "week-sim"
memory buffer list --unprocessed --pretty
memory buffer process <buffer_id>

memory notes create --title "..." --content "..." --tags "topic-a,tag-b" --pretty
memory notes update <note_id> --title "..." --content "..." --pretty
memory notes delete <note_id>

memory notes links link --source <id1> --target <id2> --relation-type "related_to" --pretty
memory notes search "..." --mode semantic --limit 5 --pretty
memory admin stats --pretty
```

## Volume plan

| Day | New notes | Updates | Deletes | Expected running total |
|---|---:|---:|---:|---:|
| 1 | 6 | 0 | 0 | 6 |
| 2 | 6 | 1 | 0 | 12 |
| 3 | 5 | 1 | 1 | 16 |
| 4 | 7 | 2 | 0 | 23 |
| 5 | 6 | 2 | 1 | 28 |
| 6 | 7 | 2 | 0 | 35 |
| 7 | 8 | 2 | 1 | 42 |

## Planned files

- `day-1.md`
- `day-2.md`
- `day-3.md`
- `day-4.md`
- `day-5.md`
- `day-6.md`
- `day-7.md`

## Review and corrections applied

Corrections made during planning pass:

1. Reduced cross-topic links to keep graph sparsity realistic.
2. Balanced note counts to stay inside the 35–50 target range.
3. Added explicit midday re-read checkpoint daily to validate cumulative buffer visibility.
4. Added scheduled deletes on days 3, 5, and 7 to exercise lifecycle churn.
