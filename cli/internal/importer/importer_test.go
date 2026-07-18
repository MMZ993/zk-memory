package importer

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	format "agents-memory-cli/internal/dump/format"
)

func TestLoadGeneratedObsidianVaultReconstructsCanonicalDocument(t *testing.T) {
	doc := format.VaultDocument{
		Version:    1,
		ExportedAt: "2026-07-17T00:00:00Z",
		Notes: []format.VaultNote{{
			ID: "note-1", Title: "Title", Content: "Body", Tags: []string{"topic"},
			CreatedAt: "2026-07-17T00:00:00Z", UpdatedAt: "2026-07-17T00:00:00Z",
			SyncStatus: "pending",
		}},
		Tags:     []format.VaultTag{{ID: "tag-1", Name: "topic", CreatedAt: "2026-07-17T00:00:00Z"}},
		NoteTags: []format.VaultNoteTag{{NoteID: "note-1", TagID: "tag-1", CreatedAt: "2026-07-17T00:00:00Z"}},
	}
	files, err := format.RenderObsidian(doc)
	if err != nil {
		t.Fatal(err)
	}
	root := t.TempDir()
	for name, data := range files {
		path := filepath.Join(root, name)
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, data, 0o600); err != nil {
			t.Fatal(err)
		}
	}

	raw, err := Load(root)
	if err != nil {
		t.Fatal(err)
	}
	var got map[string]any
	if err := json.Unmarshal(raw, &got); err != nil {
		t.Fatal(err)
	}
	notes := got["notes"].([]any)
	note := notes[0].(map[string]any)
	if note["id"] != "note-1" || note["content"] != "Body" {
		t.Fatalf("unexpected note: %#v", note)
	}
	if len(got["tags"].([]any)) != 1 || len(got["note_tags"].([]any)) != 1 {
		t.Fatalf("manifest entities missing: %#v", got)
	}
}

func TestResolveTagIDsReusesExistingTagIdentityByNormalizedName(t *testing.T) {
	raw := json.RawMessage(`{
		"version":1,
		"tags":[{"id":"generated-tag","name":" Topic ","created_at":"2026-07-17T00:00:00Z"}],
		"note_tags":[{"note_id":"note-1","tag_id":"generated-tag","created_at":"2026-07-17T00:00:00Z"}]
	}`)

	resolved, err := ResolveTagIDs(raw, map[string]string{"topic": "database-tag"})
	if err != nil {
		t.Fatal(err)
	}
	var document struct {
		Tags []struct {
			ID string `json:"id"`
		} `json:"tags"`
		NoteTags []struct {
			TagID string `json:"tag_id"`
		} `json:"note_tags"`
	}
	if err := json.Unmarshal(resolved, &document); err != nil {
		t.Fatal(err)
	}
	if document.Tags[0].ID != "database-tag" || document.NoteTags[0].TagID != "database-tag" {
		t.Fatalf("existing tag identity was not reused: %#v", document)
	}
}

func TestLoadRejectsSymlinkBufferDirectory(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "zk-memory-manifest.json"), []byte(`{"version":1,"tags":[],"note_tags":[],"relation_types":[],"links":[]}`), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(t.TempDir(), filepath.Join(root, "buffer")); err != nil {
		t.Fatal(err)
	}
	if _, err := Load(root); err == nil {
		t.Fatal("expected symlink buffer directory rejection")
	}
}

func TestLoadRejectsSymlinkManifest(t *testing.T) {
	root := t.TempDir()
	target := filepath.Join(t.TempDir(), "outside.json")
	if err := os.WriteFile(target, []byte(`{"version":1}`), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(target, filepath.Join(root, "zk-memory-manifest.json")); err != nil {
		t.Fatal(err)
	}
	if _, err := Load(root); err == nil {
		t.Fatal("expected symlink manifest rejection")
	}
}

func TestLoadSingleGeneratedNoteUsesMetadataAndIgnoresProjection(t *testing.T) {
	doc := format.VaultDocument{Version: 1, Notes: []format.VaultNote{{
		ID: "source", Title: "Source", Content: "Body\n\n<!-- zk-memory:related:start -->\nlegitimate", Tags: []string{"topic"},
		CreatedAt: "2026-07-17T00:00:00Z", UpdatedAt: "2026-07-17T00:00:00Z",
		SyncStatus: "pending", Links: []format.ResolvedLink{{
			ID: "link-1", TargetID: "target", TargetTitle: "Target",
			RelationTypeID: "relation-1", RelationType: "references",
			CreatedAt: "2026-07-17T00:00:00Z",
		}},
	}}}
	files, err := format.RenderWikiJS(doc)
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(t.TempDir(), "source.md")
	if err := os.WriteFile(path, files["source.md"], 0o600); err != nil {
		t.Fatal(err)
	}

	raw, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	var got map[string]any
	if err := json.Unmarshal(raw, &got); err != nil {
		t.Fatal(err)
	}
	note := got["notes"].([]any)[0].(map[string]any)
	if note["content"] != "Body\n\n<!-- zk-memory:related:start -->\nlegitimate" {
		t.Fatalf("projection handling changed body: %q", note["content"])
	}
	if len(got["links"].([]any)) != 1 || len(got["relation_types"].([]any)) != 0 {
		t.Fatalf("single-file link metadata was guessed or lost: %#v", got)
	}
	if len(got["tags"].([]any)) != 1 || len(got["note_tags"].([]any)) != 1 {
		t.Fatalf("frontmatter tag dependencies missing: %#v", got)
	}
}
