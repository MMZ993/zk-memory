package cmd

import (
	"fmt"
	"strings"

	"agents-memory-cli/internal/client"
	"github.com/spf13/cobra"
)

var notesCmd = &cobra.Command{
	Use:   "notes",
	Short: "Manage notes",
}

// ---------- search ----------

var (
	searchMode      string
	searchLimit     int
	searchThreshold float64
	searchTags      []string
)

var notesSearchCmd = &cobra.Command{
	Use:   "search <query>",
	Short: "Search notes",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		resp, err := c.SearchNotes(args[0], client.SearchOpts{
			Mode:      searchMode,
			Limit:     searchLimit,
			Threshold: searchThreshold,
			Tags:      searchTags,
		})
		if err != nil {
			fatal("%v", err)
		}
		printJSON(resp)
	},
}

// ---------- create ----------

var (
	createTitle   string
	createContent string
	createSummary string
	createTags    string
)

var notesCreateCmd = &cobra.Command{
	Use:   "create",
	Short: "Create a note",
	Run: func(cmd *cobra.Command, args []string) {
		if err := validateNotesCreateInput(createTitle, createContent); err != nil {
			fatal("%v", err)
		}
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		req := client.CreateNoteRequest{
			Title:   createTitle,
			Content: createContent,
			Summary: createSummary,
		}
		if createTags != "" {
			req.Tags = splitTags(createTags)
		}
		note, err := c.CreateNote(req)
		if err != nil {
			fatal("%v", err)
		}
		printJSON(note)
	},
}

// ---------- list ----------

var (
	listTags   string
	listSort   string
	listOrder  string
	listLimit  int
	listOffset int
)

var notesListCmd = &cobra.Command{
	Use:   "list",
	Short: "List notes",
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		notes, err := c.ListNotes(client.ListOpts{
			Tags:   splitTagsOpt(listTags),
			Sort:   listSort,
			Order:  listOrder,
			Limit:  listLimit,
			Offset: listOffset,
		})
		if err != nil {
			fatal("%v", err)
		}
		printJSON(notes)
	},
}

// ---------- get ----------

var notesGetCmd = &cobra.Command{
	Use:   "get <id>",
	Short: "Get a note by ID",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		note, err := c.GetNote(args[0])
		if err != nil {
			fatal("%v", err)
		}
		printJSON(note)
	},
}

// ---------- update ----------

var (
	updateTitle   string
	updateContent string
	updateSummary string
	updateTags    string
)

var notesUpdateCmd = &cobra.Command{
	Use:   "update <id>",
	Short: "Update a note",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		req := client.UpdateNoteRequest{}
		if cmd.Flags().Changed("title") {
			req.Title = &updateTitle
		}
		if cmd.Flags().Changed("content") {
			req.Content = &updateContent
		}
		if cmd.Flags().Changed("summary") {
			req.Summary = &updateSummary
		}
		if cmd.Flags().Changed("tags") {
			req.Tags = splitTags(updateTags)
		}
		note, err := c.UpdateNote(args[0], req)
		if err != nil {
			fatal("%v", err)
		}
		printJSON(note)
	},
}

// ---------- delete ----------

var notesDeleteCmd = &cobra.Command{
	Use:   "delete <id>",
	Short: "Delete a note",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		if err := c.DeleteNote(args[0]); err != nil {
			fatal("%v", err)
		}
		printJSON(map[string]string{"status": "deleted", "id": args[0]})
	},
}

// ---------- helpers ----------

func splitTags(s string) []string {
	parts := strings.Split(s, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		if t := strings.TrimSpace(p); t != "" {
			out = append(out, t)
		}
	}
	return out
}

func splitTagsOpt(s string) []string {
	if s == "" {
		return nil
	}
	return splitTags(s)
}

func validateNotesCreateInput(title string, content string) error {
	if title == "" || content == "" {
		return fmt.Errorf("--title and --content are required")
	}
	return nil
}

func init() {
	// search flags
	notesSearchCmd.Flags().StringVar(&searchMode, "mode", "", "Search mode: semantic|keyword|hybrid")
	notesSearchCmd.Flags().IntVar(&searchLimit, "limit", 0, "Max results")
	notesSearchCmd.Flags().Float64Var(&searchThreshold, "threshold", 0, "Min similarity score (0-1)")
	notesSearchCmd.Flags().StringSliceVar(&searchTags, "tags", nil, "Filter by tags")

	// create flags
	notesCreateCmd.Flags().StringVar(&createTitle, "title", "", "Note title (required)")
	notesCreateCmd.Flags().StringVar(&createContent, "content", "", "Note content (required)")
	notesCreateCmd.Flags().StringVar(&createSummary, "summary", "", "Short summary")
	notesCreateCmd.Flags().StringVar(&createTags, "tags", "", "Comma-separated tags")

	// list flags
	notesListCmd.Flags().StringVar(&listTags, "tags", "", "Comma-separated tags to filter")
	notesListCmd.Flags().StringVar(&listSort, "sort", "", "Sort field: created_at|updated_at")
	notesListCmd.Flags().StringVar(&listOrder, "order", "", "Sort order: asc|desc")
	notesListCmd.Flags().IntVar(&listLimit, "limit", 0, "Max results")
	notesListCmd.Flags().IntVar(&listOffset, "offset", 0, "Pagination offset")

	// update flags
	notesUpdateCmd.Flags().StringVar(&updateTitle, "title", "", "New title")
	notesUpdateCmd.Flags().StringVar(&updateContent, "content", "", "New content")
	notesUpdateCmd.Flags().StringVar(&updateSummary, "summary", "", "New summary")
	notesUpdateCmd.Flags().StringVar(&updateTags, "tags", "", "Comma-separated tags (replaces all)")

	notesCmd.AddCommand(
		notesSearchCmd,
		notesCreateCmd,
		notesListCmd,
		notesGetCmd,
		notesUpdateCmd,
		notesDeleteCmd,
	)
}
