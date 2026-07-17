package format

import (
	"encoding/json"
	"strings"
	"testing"
)

func stringPointer(value string) *string { return &value }

func TestRenderObsidianUsesStablePathsAndPreservesMetadata(t *testing.T) {
	doc := VaultDocument{
		Version: 1,
		Notes: []VaultNote{
			{ID: "note-a", Title: "Duplicate", Content: "body", Summary: stringPointer("summary"), Tags: []string{"tag"}, CreatedAt: "2026-01-01T01:02:03Z", UpdatedAt: "2026-01-02T01:02:03Z", Synced: true, SyncStatus: "synced", Links: []ResolvedLink{{ID: "link-1", TargetID: "note-b", TargetTitle: "Renamed", RelationTypeID: "rel-1", RelationType: "related", Description: stringPointer("context"), CreatedAt: "2026-01-03T01:02:03Z"}}},
			{ID: "note-b", Title: "Duplicate", Content: "target", CreatedAt: "2026-01-01T01:02:03Z", UpdatedAt: "2026-01-02T01:02:03Z"},
		},
		Buffers:       []VaultBuffer{{ID: "buffer-1", Content: "inbox", Meta: map[string]any{"source": "test"}, CreatedAt: "2026-01-01T01:02:03Z", UpdatedAt: "2026-01-02T01:02:03Z"}},
		Tags:          []VaultTag{{ID: "tag-1", Name: "tag", CreatedAt: "2026-01-01T01:02:03Z"}},
		RelationTypes: []VaultRelationType{{ID: "rel-1", Name: "related", CreatedAt: "2026-01-01T01:02:03Z"}},
		Links:         []VaultLink{{ID: "link-1", SourceID: "note-a", TargetID: "note-b", RelationTypeID: "rel-1", Description: stringPointer("hostile -->\ntext"), CreatedAt: "2026-01-03T01:02:03Z"}},
	}

	files, err := RenderObsidian(doc)
	if err != nil {
		t.Fatalf("RenderObsidian(): %v", err)
	}
	for _, path := range []string{"note-a.md", "note-b.md", "buffer/buffer-1.md", "zk-memory-manifest.json"} {
		if _, ok := files[path]; !ok {
			t.Errorf("missing %s", path)
		}
	}
	note := string(files["note-a.md"])
	for _, expected := range []string{"id: \"note-a\"", "summary: \"summary\"", "created_at: \"2026-01-01T01:02:03Z\"", "sync_status: \"synced\"", "<!-- zk-memory:links:start -->", "[[note-b|Renamed]]", "zk-memory-link-base64:", "<!-- zk-memory:links:end -->"} {
		if !strings.Contains(note, expected) {
			t.Errorf("note missing %q:\n%s", expected, note)
		}
	}
	manifest := string(files["zk-memory-manifest.json"])
	var decoded struct {
		Links []VaultLink `json:"links"`
	}
	if err := json.Unmarshal([]byte(manifest), &decoded); err != nil {
		t.Fatal(err)
	}
	if len(decoded.Links) != 1 || decoded.Links[0].Description == nil || *decoded.Links[0].Description != "hostile -->\ntext" {
		t.Errorf("structured link metadata missing:\n%s", manifest)
	}
	buffer := string(files["buffer/buffer-1.md"])
	if !strings.Contains(buffer, "meta_json: '{\"source\":\"test\"}'") || !strings.Contains(buffer, "processed: false") {
		t.Errorf("buffer metadata not preserved:\n%s", buffer)
	}
}

func TestYAMLFrontmatterEscapesControlCharacters(t *testing.T) {
	files, err := RenderObsidian(VaultDocument{Notes: []VaultNote{{ID: "safe", Title: "line\r\ntab\tcontrol\x01"}}})
	if err != nil {
		t.Fatal(err)
	}
	text := string(files["safe.md"])
	if strings.Contains(text, "line\r") || strings.ContainsRune(text, '\x01') {
		t.Fatalf("raw control character in frontmatter: %q", text)
	}
	if !strings.Contains(text, `title: "line\r\ntab\tcontrol\x01"`) {
		t.Fatalf("escaped title missing: %q", text)
	}
}

func TestRenderObsidianPreservesNullAndEmptyValues(t *testing.T) {
	empty := ""
	files, err := RenderObsidian(VaultDocument{Notes: []VaultNote{
		{ID: "null", Summary: nil},
		{ID: "empty", Summary: &empty},
	}})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(files["null.md"]), "summary: null") {
		t.Error("null summary was not preserved")
	}
	if !strings.Contains(string(files["empty.md"]), `summary: ""`) {
		t.Error("empty summary was not preserved")
	}
}

func TestRenderObsidianRejectsTraversalID(t *testing.T) {
	_, err := RenderObsidian(VaultDocument{Notes: []VaultNote{{ID: "../outside"}}})
	if err == nil {
		t.Fatal("expected traversal ID to be rejected")
	}
}
