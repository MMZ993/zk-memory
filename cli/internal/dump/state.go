package dump

import (
	"encoding/json"
	"fmt"
	"os"
)

// State is persisted to the state file after each successful dump.
type State struct {
	DumpedAt string            `json:"dumped_at"` // RFC3339 UTC
	Format   string            `json:"format"`
	Stats    DumpStats         `json:"stats"`
	Files    map[string]string `json:"files,omitempty"` // relative path → SHA-256 content hash
}

// DumpStats holds summary counts saved to the state file.
type DumpStats struct {
	NotesDumped int `json:"notes_dumped"`
	NotesTotal  int `json:"notes_total"`
	Links       int `json:"links"`
	Tags        int `json:"tags"`
}

// ReadState reads the state file at path.
// Returns nil, nil if the file does not exist.
func ReadState(path string) (*State, error) {
	data, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	var s State
	if err := json.Unmarshal(data, &s); err != nil {
		return nil, fmt.Errorf("parse state file: %w", err)
	}
	return &s, nil
}

// WriteState writes s to path, creating or replacing the file.
func WriteState(path string, s State) error {
	if info, err := os.Lstat(path); err == nil && info.Mode()&os.ModeSymlink != 0 {
		return fmt.Errorf("refuse symlink state destination %s", path)
	}
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}
