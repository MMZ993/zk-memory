package cmd

import (
	"encoding/json"
	"fmt"

	"agents-memory-cli/internal/client"
	"github.com/spf13/cobra"
)

var bufferCmd = &cobra.Command{
	Use:   "buffer",
	Short: "Manage buffer notes",
}

var newBufferClient = client.New

// ---------- add ----------

var (
	bufferAddContent string
	bufferAddSource  string
	bufferAddMeta    string
)

var bufferAddCmd = &cobra.Command{
	Use:   "add",
	Short: "Add a buffer note",
	Run: func(cmd *cobra.Command, args []string) {
		if bufferAddContent == "" {
			fatal("--content is required")
		}
		c, err := newBufferClient()
		if err != nil {
			fatal("%v", err)
		}

		req := client.CreateBufferRequest{Content: bufferAddContent}

		// Build meta: --meta wins; --source is a shortcut that sets meta.source
		if bufferAddMeta != "" {
			if !json.Valid([]byte(bufferAddMeta)) {
				fatal("--meta must be valid JSON")
			}
			req.Meta = json.RawMessage(bufferAddMeta)
		} else if bufferAddSource != "" {
			b, _ := json.Marshal(map[string]string{"source": bufferAddSource})
			req.Meta = json.RawMessage(b)
		}

		note, err := c.AddBuffer(req)
		if err != nil {
			fatal("%v", err)
		}
		printJSON(note)
	},
}

// ---------- list ----------

var (
	bufferListProcessed   bool
	bufferListUnprocessed bool
	bufferListAll         bool
	bufferListLimit       int
	bufferListOffset      int
)

var bufferListCmd = &cobra.Command{
	Use:   "list",
	Short: "List buffer notes",
	Run: func(cmd *cobra.Command, args []string) {
		opts, err := buildBufferListOpts(bufferListProcessed, bufferListUnprocessed, bufferListAll, bufferListLimit, bufferListOffset)
		if err != nil {
			fatal("%v", err)
		}

		c, err := newBufferClient()
		if err != nil {
			fatal("%v", err)
		}

		notes, err := c.ListBuffer(opts)
		if err != nil {
			fatal("%v", err)
		}
		printJSON(notes)
	},
}

// ---------- get ----------

var bufferGetCmd = &cobra.Command{
	Use:   "get <id>",
	Short: "Get a buffer note by ID",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := newBufferClient()
		if err != nil {
			fatal("%v", err)
		}
		note, err := c.GetBuffer(args[0])
		if err != nil {
			fatal("%v", err)
		}
		printJSON(note)
	},
}

// ---------- delete ----------

var bufferDeleteCmd = &cobra.Command{
	Use:   "delete <id>",
	Short: "Delete a buffer note",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := newBufferClient()
		if err != nil {
			fatal("%v", err)
		}
		if err := c.DeleteBuffer(args[0]); err != nil {
			fatal("%v", err)
		}
		printJSON(map[string]string{"status": "deleted", "id": args[0]})
	},
}

// ---------- process ----------

var bufferProcessCmd = &cobra.Command{
	Use:   "process <id>",
	Short: "Mark a buffer note as processed",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := newBufferClient()
		if err != nil {
			fatal("%v", err)
		}
		note, err := c.ProcessBuffer(args[0])
		if err != nil {
			fatal("%v", err)
		}
		printJSON(note)
	},
}

// ---------- cleanup ----------

var bufferCleanupCmd = &cobra.Command{
	Use:   "cleanup",
	Short: "Delete old processed buffer notes",
	Run: func(cmd *cobra.Command, args []string) {
		c, err := newBufferClient()
		if err != nil {
			fatal("%v", err)
		}
		result, err := c.CleanupBuffer()
		if err != nil {
			fatal("%v", err)
		}
		// Friendly summary when --pretty
		if pretty {
			if disabled, ok := result["disabled"].(bool); ok && disabled {
				fmt.Println("cleanup disabled (BUFFER_RETENTION_DAYS=0)")
				return
			}
			deleted := int(result["deleted"].(float64))
			fmt.Printf("deleted %d processed buffer note(s)\n", deleted)
			return
		}
		printJSON(result)
	},
}

// resolveProcessedFilter maps mutually exclusive buffer-list flags to an API filter.
// With no flag, it returns processed=false; --all returns no filter.
func resolveProcessedFilter(processed bool, unprocessed bool, all bool) (*bool, error) {
	selected := 0
	for _, enabled := range []bool{processed, unprocessed, all} {
		if enabled {
			selected++
		}
	}
	if selected > 1 {
		return nil, fmt.Errorf("--processed, --unprocessed, and --all are mutually exclusive")
	}
	if all {
		return nil, nil
	}
	if processed {
		t := true
		return &t, nil
	}
	if unprocessed {
		f := false
		return &f, nil
	}
	f := false
	return &f, nil
}

// buildBufferListOpts constructs API list options from the buffer-list CLI flags.
func buildBufferListOpts(processed bool, unprocessed bool, all bool, limit int, offset int) (client.BufferListOpts, error) {
	processedFilter, err := resolveProcessedFilter(processed, unprocessed, all)
	if err != nil {
		return client.BufferListOpts{}, err
	}

	return client.BufferListOpts{
		Processed: processedFilter,
		Limit:     limit,
		Offset:    offset,
	}, nil
}

func init() {
	// add flags
	bufferAddCmd.Flags().StringVar(&bufferAddContent, "content", "", "Buffer note content (required)")
	bufferAddCmd.Flags().StringVar(&bufferAddSource, "source", "", "Source label (sets meta.source)")
	bufferAddCmd.Flags().StringVar(&bufferAddMeta, "meta", "", "Raw JSON metadata (overrides --source)")

	// list flags
	bufferListCmd.Flags().BoolVar(&bufferListProcessed, "processed", false, "Show only processed notes (mutually exclusive with --unprocessed and --all)")
	bufferListCmd.Flags().BoolVar(&bufferListUnprocessed, "unprocessed", false, "Show only unprocessed notes (the default; mutually exclusive with --processed and --all)")
	bufferListCmd.Flags().BoolVar(&bufferListAll, "all", false, "Show all notes (mutually exclusive with --processed and --unprocessed)")
	bufferListCmd.Flags().IntVar(&bufferListLimit, "limit", 0, "Max results")
	bufferListCmd.Flags().IntVar(&bufferListOffset, "offset", 0, "Pagination offset")

	bufferCmd.AddCommand(
		bufferAddCmd,
		bufferListCmd,
		bufferGetCmd,
		bufferDeleteCmd,
		bufferProcessCmd,
		bufferCleanupCmd,
	)
}
