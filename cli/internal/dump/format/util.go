package format

import (
	"strings"
	"unicode"
)

// buildFilenames returns a map of note ID → output filename (without extension)
// for a set of notes, handling collisions by appending a short ID suffix.
// ext should include the dot, e.g. ".md".
func buildFilenames(notes []EnrichedNote, sanitize func(string) string, ext string) map[string]string {
	// First pass: assign preferred names
	type candidate struct {
		noteID string
		base   string
	}
	seen := make(map[string][]candidate)
	for _, n := range notes {
		base := sanitize(n.Title)
		if base == "" {
			base = n.ID
		}
		seen[base] = append(seen[base], candidate{noteID: n.ID, base: base})
	}

	out := make(map[string]string, len(notes))
	for base, candidates := range seen {
		if len(candidates) == 1 {
			out[candidates[0].noteID] = base + ext
		} else {
			// Collision: append first 8 chars of ID
			for _, c := range candidates {
				suffix := c.noteID
				if len(suffix) > 8 {
					suffix = suffix[:8]
				}
				out[c.noteID] = base + "-" + suffix + ext
			}
		}
	}
	return out
}

// sanitizeObsidian removes characters invalid in Obsidian filenames.
// Keeps spaces (Obsidian handles them), replaces / \ : * ? " < > | with -.
func sanitizeObsidian(title string) string {
	var b strings.Builder
	for _, r := range title {
		switch r {
		case '/', '\\', ':', '*', '?', '"', '<', '>', '|', '\x00':
			b.WriteRune('-')
		default:
			b.WriteRune(r)
		}
	}
	return strings.TrimSpace(b.String())
}

// slugify converts a title to a URL-safe slug for Wiki.js.
// Lowercases, replaces spaces and non-alphanumeric with hyphens, collapses runs.
func slugify(title string) string {
	var b strings.Builder
	prev := '-'
	for _, r := range strings.ToLower(title) {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			b.WriteRune(r)
			prev = r
		} else if prev != '-' {
			b.WriteRune('-')
			prev = '-'
		}
	}
	return strings.Trim(b.String(), "-")
}

// yamlQuoteTitle wraps a title in double quotes for YAML frontmatter,
// escaping any double quotes in the value.
func yamlQuoteTitle(s string) string {
	return `"` + strings.ReplaceAll(s, `"`, `\"`) + `"`
}
