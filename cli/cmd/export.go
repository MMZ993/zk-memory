package cmd

import (
	"agents-memory-cli/internal/client"
	"github.com/spf13/cobra"
)

var exportCmd = &cobra.Command{
	Use:   "export",
	Short: "Export data from the memory system",
}

// ---------- all ----------

var exportAllCmd = &cobra.Command{
	Use:   "all",
	Short: "Export a versioned full JSON snapshot",
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		data, err := c.ExportAll()
		if err != nil {
			fatal("%v", err)
		}
		printRawJSON(data)
	},
}

// ---------- notes ----------

var exportNotesCmd = &cobra.Command{
	Use:   "notes",
	Short: "Export notes only",
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		data, err := c.ExportNotes()
		if err != nil {
			fatal("%v", err)
		}
		printRawJSON(data)
	},
}

// ---------- buffer ----------

var exportBufferCmd = &cobra.Command{
	Use:   "buffer",
	Short: "Export buffer notes only",
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		data, err := c.ExportBuffer()
		if err != nil {
			fatal("%v", err)
		}
		printRawJSON(data)
	},
}

func init() {
	exportCmd.AddCommand(exportAllCmd, exportNotesCmd, exportBufferCmd)
}
