package format

import (
	"strings"
	"testing"
)

func TestRenderWikiJSUsesStableRoutesAndMarkedRelatedSection(t *testing.T) {
	doc := VaultDocument{Version: 1, Notes: []VaultNote{
		{ID: "note-a", Title: "Source", Content: "body", CreatedAt: "2026-01-01T01:02:03Z", UpdatedAt: "2026-01-02T01:02:03Z", Links: []ResolvedLink{{ID: "link-1", TargetID: "note-b", TargetTitle: "Renamed Target", RelationTypeID: "rel-1", RelationType: "related"}}},
		{ID: "note-b", Title: "Target", Content: "target"},
	}, Buffers: []VaultBuffer{{ID: "buffer-1", Content: "inbox"}}}
	files, err := RenderWikiJS(doc)
	if err != nil {
		t.Fatalf("RenderWikiJS(): %v", err)
	}
	for _, path := range []string{"note-a.md", "note-b.md", "buffer/buffer-1.md", "zk-memory-manifest.json"} {
		if _, ok := files[path]; !ok {
			t.Errorf("missing %s", path)
		}
	}
	note := string(files["note-a.md"])
	for _, expected := range []string{"id: \"note-a\"", "route: \"/note-a\"", "<!-- zk-memory:related:start -->", "[Renamed Target](/note-b)", "<!-- zk-memory:related:end -->"} {
		if !strings.Contains(note, expected) {
			t.Errorf("note missing %q:\n%s", expected, note)
		}
	}
}
