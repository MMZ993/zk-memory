package format

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"strings"
)

// RenderObsidian renders a complete ID-stable Obsidian vault inventory.
func RenderObsidian(doc VaultDocument) (map[string][]byte, error) {
	files := make(map[string][]byte, len(doc.Notes)+len(doc.Buffers)+1)
	for _, note := range doc.Notes {
		if err := validateID(note.ID); err != nil {
			return nil, err
		}
		for _, link := range note.Links {
			if err := validateID(link.TargetID); err != nil {
				return nil, err
			}
		}
		files[note.ID+".md"] = []byte(renderObsidianNote(note))
	}
	for _, buffer := range doc.Buffers {
		if err := validateID(buffer.ID); err != nil {
			return nil, err
		}
		content, err := renderBuffer(buffer)
		if err != nil {
			return nil, err
		}
		files["buffer/"+buffer.ID+".md"] = []byte(content)
	}
	manifest, err := renderManifest(doc)
	if err != nil {
		return nil, err
	}
	files["zk-memory-manifest.json"] = manifest
	return files, nil
}

func renderObsidianNote(n VaultNote) string {
	var b strings.Builder
	b.WriteString("---\n")
	writeNoteFrontmatter(&b, n)
	b.WriteString("---\n\n" + n.Content)
	if len(n.Links) > 0 {
		b.WriteString("\n\n<!-- zk-memory:links:start -->\n## Links\n\n")
		for _, link := range n.Links {
			fmt.Fprintf(&b, "- [[%s|%s]]", projectionText(link.TargetID), projectionText(link.TargetTitle))
			if link.RelationType != "" {
				fmt.Fprintf(&b, " — %s", projectionText(link.RelationType))
			}
			if link.Description != nil && *link.Description != "" {
				fmt.Fprintf(&b, ": %s", projectionText(*link.Description))
			}
			fmt.Fprintf(&b, " <!-- zk-memory-link-base64: %s -->\n", linkMetadata(link))
		}
		b.WriteString("<!-- zk-memory:links:end -->")
	}
	return b.String()
}

func writeNoteFrontmatter(b *strings.Builder, n VaultNote) {
	fmt.Fprintf(b, "zk_memory_version: 1\nid: %s\ntitle: %s\nsummary: %s\n", yamlQuoteTitle(n.ID), yamlQuoteTitle(n.Title), yamlNullable(n.Summary))
	b.WriteString("tags:")
	if len(n.Tags) == 0 {
		b.WriteString(" []\n")
	} else {
		b.WriteByte('\n')
		for _, tag := range n.Tags {
			fmt.Fprintf(b, "  - %s\n", yamlQuoteTitle(tag))
		}
	}
	fmt.Fprintf(b, "created_at: %s\nupdated_at: %s\nsynced: %t\nsync_status: %s\nsync_attempts: %d\n", yamlQuoteTitle(n.CreatedAt), yamlQuoteTitle(n.UpdatedAt), n.Synced, yamlQuoteTitle(n.SyncStatus), n.SyncAttempts)
	fmt.Fprintf(b, "sync_last_error: %s\nsync_last_attempt_at: %s\nsync_last_success_at: %s\n", yamlNullable(n.SyncLastError), yamlNullable(n.SyncLastAttemptAt), yamlNullable(n.SyncLastSuccessAt))
}

func linkMetadata(link ResolvedLink) string {
	data, _ := json.Marshal(link)
	return base64.StdEncoding.EncodeToString(data)
}

func projectionText(value string) string {
	value = strings.ReplaceAll(value, "\r", " ")
	value = strings.ReplaceAll(value, "\n", " ")
	value = strings.ReplaceAll(value, "<!--", "&lt;!--")
	value = strings.ReplaceAll(value, "-->", "--&gt;")
	value = strings.ReplaceAll(value, "[[", "\\[\\[")
	value = strings.ReplaceAll(value, "]]", "\\]\\]")
	return value
}

func renderBuffer(n VaultBuffer) (string, error) {
	meta, err := json.Marshal(n.Meta)
	if err != nil {
		return "", fmt.Errorf("marshal buffer %s metadata: %w", n.ID, err)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "---\nzk_memory_version: 1\ntype: buffer\nid: %s\nmeta_json: '%s'\ncreated_at: %s\nupdated_at: %s\nprocessed: %t\nprocessed_at: %s\n---\n\n%s", yamlQuoteTitle(n.ID), strings.ReplaceAll(string(meta), "'", "''"), yamlQuoteTitle(n.CreatedAt), yamlQuoteTitle(n.UpdatedAt), n.Processed, yamlNullable(n.ProcessedAt), n.Content)
	return b.String(), nil
}

func renderManifest(doc VaultDocument) ([]byte, error) {
	manifest := struct {
		Version       int                 `json:"version"`
		Tags          []VaultTag          `json:"tags"`
		NoteTags      []VaultNoteTag      `json:"note_tags"`
		RelationTypes []VaultRelationType `json:"relation_types"`
		Links         []VaultLink         `json:"links"`
	}{doc.Version, doc.Tags, doc.NoteTags, doc.RelationTypes, doc.Links}
	data, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		return nil, fmt.Errorf("marshal manifest: %w", err)
	}
	return append(data, '\n'), nil
}
