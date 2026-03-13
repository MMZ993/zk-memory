package cmd

import (
	"agents-memory-cli/internal/client"
	"github.com/spf13/cobra"
)

var tagsCmd = &cobra.Command{
	Use:   "tags",
	Short: "Manage global tags",
}

// ---------- list ----------

var (
	tagsListLimit  int
	tagsListOffset int
)

var tagsListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all tags",
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		tags, err := c.ListTags(client.TagListOpts{
			Limit:  tagsListLimit,
			Offset: tagsListOffset,
		})
		if err != nil {
			fatal("%v", err)
		}
		printJSON(tags)
	},
}

// ---------- create ----------

var tagsCreateCmd = &cobra.Command{
	Use:   "create <name>",
	Short: "Create a tag",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		tag, err := c.CreateTag(args[0])
		if err != nil {
			fatal("%v", err)
		}
		printJSON(tag)
	},
}

func init() {
	tagsListCmd.Flags().IntVar(&tagsListLimit, "limit", 0, "Max results")
	tagsListCmd.Flags().IntVar(&tagsListOffset, "offset", 0, "Pagination offset")

	tagsCmd.AddCommand(tagsListCmd, tagsCreateCmd)
}
