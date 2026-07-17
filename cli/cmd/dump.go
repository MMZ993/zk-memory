package cmd

import (
	"fmt"
	"time"

	"agents-memory-cli/internal/client"
	"agents-memory-cli/internal/dump"
	"github.com/spf13/cobra"
)

var dumpCmd = &cobra.Command{
	Use:   "dump",
	Short: "Export notes to local files",
	Long: `Export notes to a local directory in Obsidian, JSON, or Wiki.js format.

On the first run a state file is saved to <output>/.dump-state.json.
Subsequent Markdown runs compare a complete inventory and only rewrite changed
files while removing stale managed files. JSON remains a complete snapshot.

If the requested --format differs from the format recorded in the state
file, the command will exit with an error. Use --force to proceed anyway.`,
	Run: func(cmd *cobra.Command, args []string) {
		if dumpOutput == "" {
			fatal("--output is required")
		}

		var since time.Time
		if dumpSince != "" {
			var err error
			since, err = parseSince(dumpSince)
			if err != nil {
				fatal("--since: %v", err)
			}
		}

		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}

		cfg := dump.Config{
			OutputDir: dumpOutput,
			Format:    dumpFormat,
			Since:     since,
			StatePath: dumpState,
			NoState:   dumpNoState,
			Force:     dumpForce,
		}

		stats, err := dump.Run(c, cfg)
		if err != nil {
			fatal("%v", err)
		}

		if pretty {
			fmt.Printf("dumped %d/%d notes, %d links, %d tags\n",
				stats.NotesDumped, stats.NotesTotal, stats.Links, stats.Tags)
			if !dumpNoState {
				statePath := dumpState
				if statePath == "" {
					statePath = dumpOutput + "/.dump-state.json"
				}
				fmt.Printf("state saved to %s\n", statePath)
			}
			return
		}
		printJSON(stats)
	},
}

var (
	dumpOutput  string
	dumpFormat  string
	dumpSince   string
	dumpState   string
	dumpNoState bool
	dumpForce   bool
)

func init() {
	dumpCmd.Flags().StringVar(&dumpOutput, "output", "", "Output directory (required)")
	dumpCmd.Flags().StringVar(&dumpFormat, "format", "obsidian", "Output format: obsidian|json|wikijs")
	dumpCmd.Flags().StringVar(&dumpSince, "since", "", "Compatibility-only ISO 8601 date; full inventory comparison determines changes")
	dumpCmd.Flags().StringVar(&dumpState, "state", "", "State file path (default: <output>/.dump-state.json)")
	dumpCmd.Flags().BoolVar(&dumpNoState, "no-state", false, "Skip reading and writing the state file")
	dumpCmd.Flags().BoolVar(&dumpForce, "force", false, "Proceed even if format mismatches the state file")
}

// parseSince accepts ISO 8601 date ("2026-03-01") or datetime ("2026-03-01T10:00:00Z").
func parseSince(s string) (time.Time, error) {
	if t, err := time.Parse(time.RFC3339, s); err == nil {
		return t, nil
	}
	if t, err := time.Parse("2006-01-02T15:04:05", s); err == nil {
		return t, nil
	}
	if t, err := time.Parse("2006-01-02", s); err == nil {
		return t, nil
	}
	return time.Time{}, fmt.Errorf("unrecognised date format %q — use 2006-01-02 or 2006-01-02T15:04:05Z", s)
}
