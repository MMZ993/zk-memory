package cmd

import (
	"agents-memory-cli/internal/client"
	"github.com/spf13/cobra"
)

var relationsCmd = &cobra.Command{
	Use:   "relations",
	Short: "Manage relation types",
}

// ---------- list ----------

var relationsListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all relation types",
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		relations, err := c.ListRelations()
		if err != nil {
			fatal("%v", err)
		}
		printJSON(relations)
	},
}

// ---------- create ----------

var (
	relCreateName            string
	relCreateDescription     string
	relCreateIsBidirectional bool
)

var relationsCreateCmd = &cobra.Command{
	Use:   "create",
	Short: "Create a relation type",
	Run: func(cmd *cobra.Command, args []string) {
		if relCreateName == "" {
			fatal("--name is required")
		}
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		rel, err := c.CreateRelation(client.CreateRelationRequest{
			Name:            relCreateName,
			Description:     relCreateDescription,
			IsBidirectional: relCreateIsBidirectional,
		})
		if err != nil {
			fatal("%v", err)
		}
		printJSON(rel)
	},
}

// ---------- get ----------

var relationsGetCmd = &cobra.Command{
	Use:   "get <id>",
	Short: "Get a relation type by ID",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		rel, err := c.GetRelation(args[0])
		if err != nil {
			fatal("%v", err)
		}
		printJSON(rel)
	},
}

// ---------- update ----------

var (
	relUpdateName            string
	relUpdateDescription     string
	relUpdateIsBidirectional bool
)

var relationsUpdateCmd = &cobra.Command{
	Use:   "update <id>",
	Short: "Update a relation type",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		req := client.UpdateRelationRequest{}
		if cmd.Flags().Changed("name") {
			req.Name = &relUpdateName
		}
		if cmd.Flags().Changed("description") {
			req.Description = &relUpdateDescription
		}
		if cmd.Flags().Changed("bidirectional") {
			req.IsBidirectional = &relUpdateIsBidirectional
		}
		rel, err := c.UpdateRelation(args[0], req)
		if err != nil {
			fatal("%v", err)
		}
		printJSON(rel)
	},
}

// ---------- delete ----------

var relationsDeleteCmd = &cobra.Command{
	Use:   "delete <id>",
	Short: "Delete a relation type",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		if err := c.DeleteRelation(args[0]); err != nil {
			fatal("%v", err)
		}
		printJSON(map[string]string{"status": "deleted", "id": args[0]})
	},
}

func init() {
	relationsCreateCmd.Flags().StringVar(&relCreateName, "name", "", "Relation type name (required)")
	relationsCreateCmd.Flags().StringVar(&relCreateDescription, "description", "", "Description")
	relationsCreateCmd.Flags().BoolVar(&relCreateIsBidirectional, "bidirectional", false, "Bidirectional relation")

	relationsUpdateCmd.Flags().StringVar(&relUpdateName, "name", "", "New name")
	relationsUpdateCmd.Flags().StringVar(&relUpdateDescription, "description", "", "New description")
	relationsUpdateCmd.Flags().BoolVar(&relUpdateIsBidirectional, "bidirectional", false, "Set bidirectional flag")

	relationsCmd.AddCommand(
		relationsListCmd,
		relationsCreateCmd,
		relationsGetCmd,
		relationsUpdateCmd,
		relationsDeleteCmd,
	)
}
