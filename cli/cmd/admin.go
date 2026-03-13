package cmd

import (
	"fmt"

	"agents-memory-cli/internal/client"
	"github.com/spf13/cobra"
)

var adminCmd = &cobra.Command{
	Use:   "admin",
	Short: "Admin operations",
}

// ---------- health ----------

var adminHealthCmd = &cobra.Command{
	Use:   "health",
	Short: "Check API health",
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		h, err := c.GetHealth()
		if err != nil {
			fatal("%v", err)
		}
		if pretty {
			fmt.Printf("status:    %s\ndatabase:  %s\nvector_db: %s\nversion:   %s\n",
				h.Status, h.Database, h.VectorDB, h.Version)
			return
		}
		printJSON(h)
	},
}

// ---------- stats ----------

var adminStatsCmd = &cobra.Command{
	Use:   "stats",
	Short: "Show system statistics",
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		stats, err := c.GetStats()
		if err != nil {
			fatal("%v", err)
		}
		printJSON(stats)
	},
}

// ---------- config ----------

var adminConfigCmd = &cobra.Command{
	Use:   "config",
	Short: "Show current configuration",
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		cfg, err := c.GetConfig()
		if err != nil {
			fatal("%v", err)
		}
		printJSON(cfg)
	},
}

// ---------- sync ----------

var adminSyncCmd = &cobra.Command{
	Use:   "sync",
	Short: "Sync embeddings for unsynced notes",
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		resp, err := c.SyncEmbeddings()
		if err != nil {
			fatal("%v", err)
		}
		if pretty {
			fmt.Printf("status: %s, pending notes: %d\n", resp.Status, resp.PendingNotes)
			return
		}
		printJSON(resp)
	},
}

// ---------- reembed ----------

var reembedCmd = &cobra.Command{
	Use:   "reembed",
	Short: "Purge and regenerate all embeddings",
}

var (
	reembedConfirm bool
)

var reembedStartCmd = &cobra.Command{
	Use:   "start",
	Short: "Start re-embedding all notes (destructive)",
	Run: func(cmd *cobra.Command, args []string) {
		if !reembedConfirm {
			fatal("pass --confirm to acknowledge this will delete and regenerate all embeddings")
		}
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		resp, err := c.Reembed("I understand this will delete and regenerate all embeddings")
		if err != nil {
			fatal("%v", err)
		}
		if pretty {
			fmt.Printf("status: %s, total notes: %d\n", resp.Status, resp.TotalNotes)
			return
		}
		printJSON(resp)
	},
}

var reembedStatusCmd = &cobra.Command{
	Use:   "status",
	Short: "Get re-embed operation status",
	Run: func(cmd *cobra.Command, args []string) {
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		resp, err := c.GetReembedStatus()
		if err != nil {
			fatal("%v", err)
		}
		if pretty {
			fmt.Printf("status: %s\n", resp.Status)
			return
		}
		printJSON(resp)
	},
}

func init() {
	reembedStartCmd.Flags().BoolVar(&reembedConfirm, "confirm", false, "Confirm destructive operation")

	reembedCmd.AddCommand(reembedStartCmd, reembedStatusCmd)
	adminCmd.AddCommand(adminHealthCmd, adminStatsCmd, adminConfigCmd, adminSyncCmd, reembedCmd)
}
