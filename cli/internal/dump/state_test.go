package dump

import (
	"os"
	"path/filepath"
	"testing"
)

func TestWriteStateRejectsSymlinkDestination(t *testing.T) {
	target := filepath.Join(t.TempDir(), "outside.json")
	statePath := filepath.Join(t.TempDir(), ".dump-state.json")
	if err := os.Symlink(target, statePath); err != nil {
		t.Fatal(err)
	}
	if err := WriteState(statePath, State{}); err == nil {
		t.Fatal("expected symlink destination to be rejected")
	}
	if _, err := os.Stat(target); !os.IsNotExist(err) {
		t.Fatal("outside target was written")
	}
}
