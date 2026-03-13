package cmd

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var pretty bool

var rootCmd = &cobra.Command{
	Use:   "memory",
	Short: "CLI for the AI agent memory system",
}

// Execute runs the root command.
func Execute() {
	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}

func init() {
	rootCmd.PersistentFlags().BoolVarP(&pretty, "pretty", "p", false, "Human-readable output")

	rootCmd.AddCommand(notesCmd)
	rootCmd.AddCommand(bufferCmd)
	rootCmd.AddCommand(tagsCmd)
	rootCmd.AddCommand(relationsCmd)
	rootCmd.AddCommand(exportCmd)
	rootCmd.AddCommand(adminCmd)
}

// printJSON writes v as compact JSON to stdout, or pretty if --pretty is set.
func printJSON(v any) {
	var b []byte
	var err error
	if pretty {
		b, err = json.MarshalIndent(v, "", "  ")
	} else {
		b, err = json.Marshal(v)
	}
	if err != nil {
		fatal("encode output: %v", err)
	}
	fmt.Println(string(b))
}

// fatal writes msg to stderr and exits 1.
func fatal(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "error: "+format+"\n", args...)
	os.Exit(1)
}
