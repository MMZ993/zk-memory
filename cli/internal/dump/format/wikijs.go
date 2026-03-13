package format

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// WriteWikiJS writes one .md file per note into outDir using Wiki.js format:
// YAML frontmatter (title, description, tags, dates) + content + ## Related section.
// Filenames are URL slugs derived from the title.
func WriteWikiJS(notes []EnrichedNote, outDir string) error {
	filenames := buildFilenames(notes, slugify, ".md")

	// Build slug map for link targets (title → slug-filename without ext)
	slugByID := make(map[string]string, len(notes))
	for _, n := range notes {
		name := filenames[n.ID]
		slugByID[n.ID] = strings.TrimSuffix(name, ".md")
	}

	for _, n := range notes {
		content := renderWikiJS(n, slugByID)
		path := filepath.Join(outDir, filenames[n.ID])
		if err := os.WriteFile(path, []byte(content), 0644); err != nil {
			return fmt.Errorf("write %s: %w", path, err)
		}
	}
	return nil
}

func renderWikiJS(n EnrichedNote, slugByID map[string]string) string {
	var b strings.Builder

	// Frontmatter
	b.WriteString("---\n")
	fmt.Fprintf(&b, "title: %s\n", yamlQuoteTitle(n.Title))
	if n.Summary != "" {
		fmt.Fprintf(&b, "description: %s\n", yamlQuoteTitle(n.Summary))
	}
	if len(n.Tags) > 0 {
		b.WriteString("tags:\n")
		for _, t := range n.Tags {
			fmt.Fprintf(&b, "  - %s\n", t)
		}
	}
	// Wiki.js uses date-only for created/updated in frontmatter
	fmt.Fprintf(&b, "created: %s\n", dateOnly(n.CreatedAt))
	fmt.Fprintf(&b, "updated: %s\n", dateOnly(n.UpdatedAt))
	b.WriteString("---\n\n")

	// Content
	b.WriteString(n.Content)

	// Related section
	if len(n.Links) > 0 {
		b.WriteString("\n\n## Related\n\n")
		for _, lnk := range n.Links {
			slug := slugByID[lnk.TargetID]
			if slug == "" {
				slug = slugify(lnk.TargetTitle)
			}
			line := fmt.Sprintf("- [%s](/%s)", lnk.TargetTitle, slug)
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

// dateOnly extracts the date portion from an ISO 8601 datetime string.
func dateOnly(s string) string {
	if len(s) >= 10 {
		return s[:10]
	}
	return s
}
