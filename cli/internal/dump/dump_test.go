package dump

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"agents-memory-cli/internal/client"
)

func TestRunJSONWritesFullExportWithoutPartialResourceRequests(t *testing.T) {
	document := `{"version":1,"exported_at":"2026-07-17T12:00:00Z","notes":[{"id":"note-1"},{"id":"note-2"}],"tags":[{"id":"tag-1"}],"note_tags":[],"relation_types":[{"id":"relation-1"}],"links":[{"id":"link-1","source_id":"note-1","target_id":"note-2","relation_type_id":"relation-1"}],"buffer_notes":[{"id":"buffer-1"}]}`
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/export" {
			t.Errorf("unexpected request path %q", r.URL.Path)
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(document))
	}))
	defer server.Close()
	t.Setenv("MEMORY_API_URL", server.URL)
	t.Setenv("MEMORY_API_KEY", "")

	apiClient, err := client.New()
	if err != nil {
		t.Fatalf("client.New(): %v", err)
	}
	outputDir := t.TempDir()
	stats, err := Run(apiClient, Config{OutputDir: outputDir, Format: "json", NoState: true})
	if err != nil {
		t.Fatalf("Run(): %v", err)
	}
	if stats.NotesTotal != 2 || stats.Links != 1 || stats.Tags != 1 {
		t.Fatalf("stats = %#v", stats)
	}

	data, err := os.ReadFile(filepath.Join(outputDir, "export.json"))
	if err != nil {
		t.Fatalf("read export.json: %v", err)
	}
	var exported struct {
		BufferNotes []json.RawMessage `json:"buffer_notes"`
	}
	if err := json.Unmarshal(data, &exported); err != nil {
		t.Fatalf("decode export.json: %v", err)
	}
	if len(exported.BufferNotes) != 1 {
		t.Fatalf("buffer notes = %d, want 1", len(exported.BufferNotes))
	}
}

func TestValidateExportRecordsAllowsLegacyOrphanedAssociations(t *testing.T) {
	doc := exportDocument{
		Notes:    []exportNote{{ID: "note-present"}},
		Tags:     []exportTag{{ID: "tag-present"}},
		NoteTags: []exportNoteTag{{NoteID: "note-deleted", TagID: "tag-present"}},
		Links:    []exportLink{{ID: "link-orphan", SourceID: "note-deleted", TargetID: "note-present", RelationTypeID: "relation-deleted"}},
	}
	if err := validateExportRecords(doc); err != nil {
		t.Fatalf("legacy orphaned records should be preserved: %v", err)
	}
}

func TestValidateExportRecordsRejectsMalformedAssociations(t *testing.T) {
	tests := []exportDocument{
		{NoteTags: []exportNoteTag{{NoteID: "", TagID: "tag"}}},
		{NoteTags: []exportNoteTag{{NoteID: "note", TagID: "tag"}, {NoteID: "note", TagID: "tag"}}},
		{Links: []exportLink{{ID: "link", SourceID: "", TargetID: "target", RelationTypeID: "relation"}}},
	}
	for index, doc := range tests {
		if err := validateExportRecords(doc); err == nil {
			t.Errorf("case %d: expected malformed association to fail", index)
		}
	}
}

func TestInvalidExportDoesNotTouchExistingFiles(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) { _, _ = fmt.Fprint(w, `{"version":2,"notes":[]}`) }))
	defer server.Close()
	t.Setenv("MEMORY_API_URL", server.URL)
	apiClient, _ := client.New()
	output := t.TempDir()
	path := filepath.Join(output, "existing.md")
	if err := os.WriteFile(path, []byte("keep"), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := Run(apiClient, Config{OutputDir: output, Format: "obsidian"}); err == nil {
		t.Fatal("expected unsupported export to fail")
	}
	data, _ := os.ReadFile(path)
	if string(data) != "keep" {
		t.Fatal("existing output was modified")
	}
}

func TestSafeOutputPathRejectsTraversal(t *testing.T) {
	if _, err := safeOutputPath(t.TempDir(), "../outside.md"); err == nil {
		t.Fatal("expected traversal path to be rejected")
	}
}

func TestMarkdownDumpReconcilesChangedAndStaleFiles(t *testing.T) {
	for _, dumpFormat := range []string{"obsidian", "wikijs"} {
		t.Run(dumpFormat, func(t *testing.T) {
			document := `{"version":1,"exported_at":"2026-07-17T12:00:00Z","notes":[{"id":"note-a","title":"Duplicate","content":"body","tags":["tag"],"created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-02T00:00:00Z"},{"id":"note-b","title":"Duplicate","content":"target","tags":[],"created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-02T00:00:00Z"}],"tags":[{"id":"tag-1","name":"tag"}],"note_tags":[],"relation_types":[{"id":"rel-1","name":"related"}],"links":[{"id":"link-1","source_id":"note-a","target_id":"note-b","relation_type_id":"rel-1"}],"buffer_notes":[{"id":"buffer-1","content":"inbox"}]}`
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) { _, _ = fmt.Fprint(w, document) }))
			defer server.Close()
			t.Setenv("MEMORY_API_URL", server.URL)
			apiClient, err := client.New()
			if err != nil {
				t.Fatal(err)
			}
			output := t.TempDir()
			if _, err := Run(apiClient, Config{OutputDir: output, Format: dumpFormat}); err != nil {
				t.Fatalf("first Run(): %v", err)
			}
			path := filepath.Join(output, "note-a.md")
			manifestPath := filepath.Join(output, "zk-memory-manifest.json")
			before, _ := os.Stat(path)
			manifestBefore, _ := os.Stat(manifestPath)
			time.Sleep(20 * time.Millisecond)
			if _, err := Run(apiClient, Config{OutputDir: output, Format: dumpFormat}); err != nil {
				t.Fatalf("unchanged Run(): %v", err)
			}
			unchanged, _ := os.Stat(path)
			if !unchanged.ModTime().Equal(before.ModTime()) {
				t.Error("unchanged note was rewritten")
			}
			manifestUnchanged, _ := os.Stat(manifestPath)
			if !manifestUnchanged.ModTime().Equal(manifestBefore.ModTime()) {
				t.Error("unchanged manifest was rewritten")
			}
			if err := os.WriteFile(path, []byte("local modification"), 0644); err != nil {
				t.Fatal(err)
			}
			if _, err := Run(apiClient, Config{OutputDir: output, Format: dumpFormat}); err != nil {
				t.Fatalf("repair Run(): %v", err)
			}
			repaired, _ := os.ReadFile(path)
			if string(repaired) == "local modification" {
				t.Error("locally modified managed note was not repaired")
			}
			time.Sleep(20 * time.Millisecond)
			document = `{"version":1,"exported_at":"2026-07-18T12:00:00Z","notes":[{"id":"note-a","title":"Renamed","content":"body","tags":[],"created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-02T00:00:00Z"}],"tags":[],"note_tags":[],"relation_types":[],"links":[],"buffer_notes":[]}`
			if _, err := Run(apiClient, Config{OutputDir: output, Format: dumpFormat}); err != nil {
				t.Fatalf("second Run(): %v", err)
			}
			after, _ := os.Stat(path)
			if !after.ModTime().After(before.ModTime()) {
				t.Error("changed projections did not rewrite note")
			}
			for _, stale := range []string{"note-b.md", "buffer/buffer-1.md"} {
				if _, err := os.Stat(filepath.Join(output, stale)); !os.IsNotExist(err) {
					t.Errorf("stale %s was not removed", stale)
				}
			}
		})
	}
}
