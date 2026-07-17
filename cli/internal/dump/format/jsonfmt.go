package format

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// WriteJSON writes the canonical full export document to export.json.
func WriteJSON(document json.RawMessage, outDir string) error {
	if !json.Valid(document) {
		return fmt.Errorf("marshal export: invalid JSON document")
	}

	var data bytes.Buffer
	if err := json.Indent(&data, document, "", "  "); err != nil {
		return fmt.Errorf("marshal export: %w", err)
	}
	data.WriteByte('\n')

	path := filepath.Join(outDir, "export.json")
	if info, err := os.Lstat(path); err == nil && info.Mode()&os.ModeSymlink != 0 {
		return fmt.Errorf("refuse symlink destination %s", path)
	}
	if err := os.WriteFile(path, data.Bytes(), 0644); err != nil {
		return fmt.Errorf("write %s: %w", path, err)
	}
	return nil
}
