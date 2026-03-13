package cmd

import (
	"agents-memory-cli/internal/client"
	"github.com/spf13/cobra"
)

var notesTagsCmd = &cobra.Command{
	Use:   "tags",
	Short: "Manage tags on a note",
}

// ---------- list ----------

var notesTagsListCmd = &cobra.Command{
	Use:   "list <note-id>",
	Short: "List tags on a note",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		tags, err := c.GetNoteTags(args[0])
		if err != nil {
			fatal("%v", err)
		}
		printJSON(tags)
	},
}

// ---------- add ----------

var notesTagsAddCmd = &cobra.Command{
	Use:   "add <note-id> <tag-name>",
	Short: "Add a tag to a note",
	Args:  cobra.ExactArgs(2),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		tag, err := c.AddNoteTag(args[0], args[1])
		if err != nil {
			fatal("%v", err)
		}
		printJSON(tag)
	},
}

// ---------- remove ----------

var notesTagsRemoveCmd = &cobra.Command{
	Use:   "remove <note-id> <tag-id>",
	Short: "Remove a tag from a note",
	Args:  cobra.ExactArgs(2),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		if err := c.RemoveNoteTag(args[0], args[1]); err != nil {
			fatal("%v", err)
		}
		printJSON(map[string]string{"status": "removed", "note_id": args[0], "tag_id": args[1]})
	},
}

func init() {
	notesTagsCmd.AddCommand(notesTagsListCmd, notesTagsAddCmd, notesTagsRemoveCmd)
	notesCmd.AddCommand(notesTagsCmd)
}
