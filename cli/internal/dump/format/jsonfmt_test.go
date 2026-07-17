package format

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestWriteJSONRejectsSymlinkDestination(t *testing.T) {
	outputDir := t.TempDir()
	target := filepath.Join(t.TempDir(), "outside.json")
	if err := os.Symlink(target, filepath.Join(outputDir, "export.json")); err != nil {
		t.Fatal(err)
	}
	if err := WriteJSON(json.RawMessage(`{"version":1}`), outputDir); err == nil {
		t.Fatal("expected symlink destination to be rejected")
	}
	if _, err := os.Stat(target); !os.IsNotExist(err) {
		t.Fatal("outside target was written")
	}
}

func TestWriteJSONWritesCanonicalExportDocument(t *testing.T) {
	document := json.RawMessage(`{"version":1,"exported_at":"2026-07-17T12:00:00Z","notes":[{"id":"note-1"}],"tags":[{"id":"tag-1"}],"note_tags":[{"note_id":"note-1","tag_id":"tag-1"}],"relation_types":[{"id":"relation-1"}],"links":[{"id":"link-1"}],"buffer_notes":[{"id":"buffer-1"}]}`)
	outputDir := t.TempDir()

	if err := WriteJSON(document, outputDir); err != nil {
		t.Fatalf("WriteJSON(): %v", err)
	}

	data, err := os.ReadFile(filepath.Join(outputDir, "export.json"))
	if err != nil {
		t.Fatalf("read export.json: %v", err)
	}
	var got, want any
	if err := json.Unmarshal(data, &got); err != nil {
		t.Fatalf("decode written document: %v", err)
	}
	if err := json.Unmarshal(document, &want); err != nil {
		t.Fatalf("decode expected document: %v", err)
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("written document = %#v, want %#v", got, want)
	}
}
