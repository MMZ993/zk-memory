package cmd

import (
	"agents-memory-cli/internal/client"
	"github.com/spf13/cobra"
)

var notesLinksCmd = &cobra.Command{
	Use:   "links",
	Short: "Manage links between notes",
}

// ---------- list ----------

var (
	linksDirection string
	linksLimit     int
)

var notesLinksListCmd = &cobra.Command{
	Use:   "list <note-id>",
	Short: "List links for a note",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		links, err := c.GetNoteLinks(args[0], client.NoteLinkListOpts{
			Direction: linksDirection,
			Limit:     linksLimit,
		})
		if err != nil {
			fatal("%v", err)
		}
		printJSON(links)
	},
}

// ---------- link ----------

var (
	linkSource       string
	linkTarget       string
	linkRelationType string
	linkDescription  string
)

var notesLinkCmd = &cobra.Command{
	Use:   "link",
	Short: "Create a link between two notes",
	Run: func(cmd *cobra.Command, args []string) {
		if linkSource == "" || linkTarget == "" || linkRelationType == "" {
			fatal("--source, --target, and --relation-type are required")
		}
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		link, err := c.CreateLink(client.CreateLinkRequest{
			SourceID:     linkSource,
			TargetID:     linkTarget,
			RelationType: linkRelationType,
			Description:  linkDescription,
		})
		if err != nil {
			fatal("%v", err)
		}
		printJSON(link)
	},
}

// ---------- unlink ----------

var notesUnlinkCmd = &cobra.Command{
	Use:   "unlink <link-id>",
	Short: "Delete a link by ID",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		if err := c.DeleteLink(args[0]); err != nil {
			fatal("%v", err)
		}
		printJSON(map[string]string{"status": "deleted", "id": args[0]})
	},
}

// ---------- graph ----------

var graphDepth int

var notesGraphCmd = &cobra.Command{
	Use:   "graph <note-id>",
	Short: "Get connected notes via graph traversal",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		resp, err := c.GetNoteGraph(args[0], graphDepth)
		if err != nil {
			fatal("%v", err)
		}
		printJSON(resp)
	},
}

func init() {
	notesLinksListCmd.Flags().StringVar(&linksDirection, "direction", "", "Direction: incoming|outgoing|all")
	notesLinksListCmd.Flags().IntVar(&linksLimit, "limit", 0, "Max results")

	notesLinkCmd.Flags().StringVar(&linkSource, "source", "", "Source note ID (required)")
	notesLinkCmd.Flags().StringVar(&linkTarget, "target", "", "Target note ID (required)")
	notesLinkCmd.Flags().StringVar(&linkRelationType, "relation-type", "", "Relation type name (required)")
	notesLinkCmd.Flags().StringVar(&linkDescription, "description", "", "Optional description")

	notesGraphCmd.Flags().IntVar(&graphDepth, "depth", 1, "Traversal depth (1-3)")

	notesLinksCmd.AddCommand(notesLinksListCmd, notesLinkCmd, notesUnlinkCmd, notesGraphCmd)
	notesCmd.AddCommand(notesLinksCmd)
}
