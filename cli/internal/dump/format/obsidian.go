package format

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// WriteObsidian writes one .md file per note into outDir using Obsidian format:
// YAML frontmatter (id, title, tags, dates) + note content + ## Links section.
func WriteObsidian(notes []EnrichedNote, outDir string) error {
	filenames := buildFilenames(notes, sanitizeObsidian, ".md")

	for _, n := range notes {
		content := renderObsidian(n)
		path := filepath.Join(outDir, filenames[n.ID])
		if err := os.WriteFile(path, []byte(content), 0644); err != nil {
			return fmt.Errorf("write %s: %w", path, err)
		}
	}
	return nil
}

func renderObsidian(n EnrichedNote) string {
	var b strings.Builder

	// Frontmatter
	b.WriteString("---\n")
	fmt.Fprintf(&b, "id: %s\n", n.ID)
	fmt.Fprintf(&b, "title: %s\n", yamlQuoteTitle(n.Title))
	if len(n.Tags) > 0 {
		fmt.Fprintf(&b, "tags: [%s]\n", strings.Join(n.Tags, ", "))
	} else {
		b.WriteString("tags: []\n")
	}
	fmt.Fprintf(&b, "created: %s\n", n.CreatedAt)
	fmt.Fprintf(&b, "updated: %s\n", n.UpdatedAt)
	b.WriteString("---\n\n")

	// Content
	b.WriteString(n.Content)

	// Links section (only if there are outgoing links)
	if len(n.Links) > 0 {
		b.WriteString("\n\n## Links\n\n")
		for _, lnk := range n.Links {
			line := fmt.Sprintf("- [[%s]]", lnk.TargetTitle)
			if lnk.RelationType != "" {
				line += " — " + lnk.RelationType
			}
			if lnk.Description != "" {
				line += ": " + lnk.Description
			}
			b.WriteString(line + "\n")
		}
	}

	return b.String()
}
