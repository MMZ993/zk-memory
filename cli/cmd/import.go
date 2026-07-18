package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"agents-memory-cli/internal/client"
	"agents-memory-cli/internal/importer"
	"github.com/spf13/cobra"
)

var (
	importSoft  bool
	importForce bool
	importType  string
	importID    string
)

var importCmd = &cobra.Command{
	Use:   "import <json-file>",
	Short: "Analyze or apply a canonical JSON import",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		if err := validateImportFlags(importSoft, importForce, importType, importID); err != nil {
			fatal("%v", err)
		}
		c, err := client.New()
		if err != nil {
			fatal("%v", err)
		}
		data, err := loadImportDocument(args[0])
		if err != nil {
			fatal("%v", err)
		}
		if filepath.Ext(args[0]) == ".md" {
			data, err = resolveStandaloneMarkdownTags(c, data)
			if err != nil {
				fatal("%v", err)
			}
		}
		mode := "dry_run"
		if importSoft {
			mode = "soft"
		} else if importForce {
			mode = "force"
		}
		report, err := c.ImportDocument(data, client.ImportOptions{
			Mode: mode, EntityType: importType, EntityID: importID,
		})
		if err != nil {
			fatal("%v", err)
		}
		printRawJSON(report)
	},
}

func loadImportDocument(path string) (json.RawMessage, error) {
	info, err := os.Lstat(path)
	if err != nil {
		return nil, fmt.Errorf("inspect import path: %w", err)
	}
	if info.Mode()&os.ModeSymlink != 0 {
		return nil, fmt.Errorf("import path must not be a symlink")
	}
	if info.IsDir() || filepath.Ext(path) == ".md" {
		return importer.Load(path)
	}
	if !info.Mode().IsRegular() {
		return nil, fmt.Errorf("JSON import path must be a regular file")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read import file: %w", err)
	}
	if !json.Valid(data) {
		return nil, fmt.Errorf("import file is not valid JSON")
	}
	return data, nil
}

func resolveStandaloneMarkdownTags(c *client.Client, data json.RawMessage) (json.RawMessage, error) {
	existingByName := map[string]string{}
	for offset := 0; ; offset += 200 {
		tags, err := c.ListTags(client.TagListOpts{Limit: 200, Offset: offset})
		if err != nil {
			return nil, fmt.Errorf("list tags for Markdown import: %w", err)
		}
		for _, tag := range tags {
			existingByName[strings.ToLower(strings.TrimSpace(tag.Name))] = tag.ID
		}
		if len(tags) < 200 {
			break
		}
	}
	return importer.ResolveTagIDs(data, existingByName)
}

func validateImportFlags(soft, force bool, entityType, entityID string) error {
	if soft && force {
		return fmt.Errorf("--soft and --force are mutually exclusive")
	}
	if (entityType == "") != (entityID == "") {
		return fmt.Errorf("--type and --id must be provided together")
	}
	validTypes := map[string]bool{
		"notes": true, "tags": true, "note_tags": true,
		"relation_types": true, "links": true, "buffer_notes": true,
	}
	if entityType != "" && !validTypes[entityType] {
		return fmt.Errorf("unsupported --type %q", entityType)
	}
	return nil
}

func init() {
	importCmd.Flags().BoolVar(&importSoft, "soft", false, "Apply clean entities and reject conflicts")
	importCmd.Flags().BoolVar(&importForce, "force", false, "Apply and overwrite conflicting entities")
	importCmd.Flags().StringVar(&importType, "type", "", "Select entity type")
	importCmd.Flags().StringVar(&importID, "id", "", "Select entity ID (note_tags use <note-id>:<tag-id>)")
}
