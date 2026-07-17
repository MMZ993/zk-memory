package format

import (
	"fmt"
	"strings"
)

// RenderWikiJS renders a complete ID-stable Wiki.js Markdown inventory.
func RenderWikiJS(doc VaultDocument) (map[string][]byte, error) {
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
		files[note.ID+".md"] = []byte(renderWikiJSNote(note))
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

func renderWikiJSNote(n VaultNote) string {
	var b strings.Builder
	b.WriteString("---\n")
	writeNoteFrontmatter(&b, n)
	fmt.Fprintf(&b, "route: %s\n---\n\n%s", yamlQuoteTitle("/"+n.ID), n.Content)
	if len(n.Links) > 0 {
		b.WriteString("\n\n<!-- zk-memory:related:start -->\n## Related\n\n")
		for _, link := range n.Links {
			fmt.Fprintf(&b, "- [%s](/%s)", projectionText(link.TargetTitle), projectionText(link.TargetID))
			if link.RelationType != "" {
				fmt.Fprintf(&b, " — %s", projectionText(link.RelationType))
			}
			if link.Description != nil && *link.Description != "" {
				fmt.Fprintf(&b, ": %s", projectionText(*link.Description))
			}
			fmt.Fprintf(&b, " <!-- zk-memory-link-base64: %s -->\n", linkMetadata(link))
		}
		b.WriteString("<!-- zk-memory:related:end -->")
	}
	return b.String()
}
