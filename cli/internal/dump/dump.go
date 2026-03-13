package dump

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"agents-memory-cli/internal/client"
	"agents-memory-cli/internal/dump/format"
)

// Config holds all parameters for a dump run.
type Config struct {
	OutputDir   string
	Format      string    // obsidian | json | wikijs
	Since       time.Time // zero value = no cutoff
	StatePath   string    // defaults to <OutputDir>/.dump-state.json
	NoState     bool
	Force       bool
	Concurrency int
}

// Run executes a dump with the given config. Returns stats on success.
func Run(c *client.Client, cfg Config) (*DumpStats, error) {
	if cfg.StatePath == "" {
		cfg.StatePath = filepath.Join(cfg.OutputDir, ".dump-state.json")
	}
	if cfg.Concurrency <= 0 {
		cfg.Concurrency = 5
	}

	// ── 1. State file checks ────────────────────────────────────────────────
	cutoff := cfg.Since
	if !cfg.NoState {
		state, err := ReadState(cfg.StatePath)
		if err != nil {
			return nil, fmt.Errorf("read state file: %w", err)
		}
		if state != nil {
			if state.Format != cfg.Format {
				if !cfg.Force {
					return nil, fmt.Errorf(
						"output directory was last dumped as %q, requested format is %q\n"+
							"use --force to overwrite, or choose a different --output directory",
						state.Format, cfg.Format,
					)
				}
				fmt.Fprintf(os.Stderr, "warning: format mismatch (was %q, now %q), proceeding with --force\n",
					state.Format, cfg.Format)
			}
			// Only use state cutoff when --since was not explicitly provided
			if cutoff.IsZero() {
				if t, err := time.Parse(time.RFC3339, state.DumpedAt); err == nil {
					cutoff = t
				}
			}
		}
	}

	// ── 2. Create output dir ─────────────────────────────────────────────────
	if err := os.MkdirAll(cfg.OutputDir, 0755); err != nil {
		return nil, fmt.Errorf("create output dir: %w", err)
	}

	// ── 3. Fetch all notes (needed for ID→title map even on incremental runs) ─
	raw, err := c.ExportNotes()
	if err != nil {
		return nil, fmt.Errorf("fetch notes: %w", err)
	}
	var allNotes []client.Note
	if err := json.Unmarshal(raw, &allNotes); err != nil {
		return nil, fmt.Errorf("parse notes: %w", err)
	}

	titleByID := make(map[string]string, len(allNotes))
	for _, n := range allNotes {
		titleByID[n.ID] = n.Title
	}

	// ── 4. Fetch all relation types → ID→name map ────────────────────────────
	relations, err := c.ListRelations()
	if err != nil {
		return nil, fmt.Errorf("fetch relation types: %w", err)
	}
	relNameByID := make(map[string]string, len(relations))
	for _, r := range relations {
		relNameByID[r.ID] = r.Name
	}

	// ── 5. Filter notes to dump ───────────────────────────────────────────────
	toDump := filterNotes(allNotes, cutoff)

	// ── 6. Fetch links concurrently ───────────────────────────────────────────
	linksByID, err := fetchLinks(c, toDump, cfg.Concurrency)
	if err != nil {
		return nil, err
	}

	// ── 7. Build EnrichedNote slice ───────────────────────────────────────────
	enriched := make([]format.EnrichedNote, 0, len(toDump))
	totalLinks := 0
	tagSet := make(map[string]struct{})

	for _, n := range toDump {
		en := format.EnrichedNote{
			ID:        n.ID,
			Title:     n.Title,
			Content:   n.Content,
			Summary:   n.Summary,
			Tags:      n.Tags,
			CreatedAt: n.CreatedAt,
			UpdatedAt: n.UpdatedAt,
			Synced:    n.Synced,
		}
		for _, t := range n.Tags {
			tagSet[t] = struct{}{}
		}
		for _, lnk := range linksByID[n.ID] {
			targetTitle := titleByID[lnk.TargetID]
			if targetTitle == "" {
				targetTitle = lnk.TargetID // fallback to ID if note was deleted
			}
			relName := relNameByID[lnk.RelationTypeID]
			if relName == "" {
				relName = lnk.RelationTypeID
			}
			en.Links = append(en.Links, format.ResolvedLink{
				ID:           lnk.ID,
				TargetID:     lnk.TargetID,
				TargetTitle:  targetTitle,
				RelationType: relName,
				Description:  lnk.Description,
			})
			totalLinks++
		}
		enriched = append(enriched, en)
	}

	// ── 8. Write files in chosen format ───────────────────────────────────────
	switch cfg.Format {
	case "obsidian":
		if err := format.WriteObsidian(enriched, cfg.OutputDir); err != nil {
			return nil, err
		}
	case "json":
		if err := format.WriteJSON(enriched, cfg.OutputDir); err != nil {
			return nil, err
		}
	case "wikijs":
		if err := format.WriteWikiJS(enriched, cfg.OutputDir); err != nil {
			return nil, err
		}
	default:
		return nil, fmt.Errorf("unknown format: %q", cfg.Format)
	}

	// ── 9. Write state file ────────────────────────────────────────────────────
	stats := DumpStats{
		NotesDumped: len(enriched),
		NotesTotal:  len(allNotes),
		Links:       totalLinks,
		Tags:        len(tagSet),
	}
	if !cfg.NoState {
		s := State{
			DumpedAt: time.Now().UTC().Format(time.RFC3339),
			Format:   cfg.Format,
			Stats:    stats,
		}
		if err := WriteState(cfg.StatePath, s); err != nil {
			return nil, fmt.Errorf("write state file: %w", err)
		}
	}

	return &stats, nil
}

// filterNotes returns notes with updated_at >= cutoff, or all notes if cutoff is zero.
func filterNotes(notes []client.Note, cutoff time.Time) []client.Note {
	if cutoff.IsZero() {
		return notes
	}
	out := make([]client.Note, 0, len(notes))
	for _, n := range notes {
		t := parseAPITime(n.UpdatedAt)
		if !t.IsZero() && !t.Before(cutoff) {
			out = append(out, n)
		}
	}
	return out
}

// parseAPITime parses the datetime strings returned by the API.
// Tries RFC3339 (with Z) first, then the naive format Python isoformat() produces.
func parseAPITime(s string) time.Time {
	if t, err := time.Parse(time.RFC3339, s); err == nil {
		return t
	}
	if t, err := time.Parse("2006-01-02T15:04:05", s); err == nil {
		return t
	}
	return time.Time{}
}

type linkResult struct {
	id    string
	links []client.NoteLink
	err   error
}

// fetchLinks fetches outgoing links for each note using a worker pool.
func fetchLinks(c *client.Client, notes []client.Note, concurrency int) (map[string][]client.NoteLink, error) {
	if len(notes) == 0 {
		return make(map[string][]client.NoteLink), nil
	}

	work := make(chan string, len(notes))
	results := make(chan linkResult, len(notes))

	for i := 0; i < concurrency; i++ {
		go func() {
			for id := range work {
				links, err := c.GetNoteLinks(id, client.NoteLinkListOpts{
					Direction: "outgoing",
					Limit:     200,
				})
				results <- linkResult{id: id, links: links, err: err}
			}
		}()
	}

	for _, n := range notes {
		work <- n.ID
	}
	close(work)

	out := make(map[string][]client.NoteLink, len(notes))
	for range notes {
		r := <-results
		if r.err != nil {
			return nil, fmt.Errorf("fetch links for note %s: %w", r.id, r.err)
		}
		out[r.id] = r.links
	}
	return out, nil
}
