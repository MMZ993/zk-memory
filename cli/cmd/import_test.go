package cmd

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadImportDocumentRejectsSymlinkJSON(t *testing.T) {
	target := filepath.Join(t.TempDir(), "target.json")
	if err := os.WriteFile(target, []byte(`{"version":1}`), 0o600); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(t.TempDir(), "import.json")
	if err := os.Symlink(target, link); err != nil {
		t.Fatal(err)
	}
	if _, err := loadImportDocument(link); err == nil {
		t.Fatal("expected symlink rejection")
	}
}

func TestValidateImportFlagsRequiresTypeAndIDTogether(t *testing.T) {
	if err := validateImportFlags(false, false, "notes", ""); err == nil {
		t.Fatal("expected selection validation error")
	}
	if err := validateImportFlags(true, true, "", ""); err == nil {
		t.Fatal("expected mutually exclusive mode error")
	}
	if err := validateImportFlags(false, false, "notes", "note-1"); err != nil {
		t.Fatalf("valid selection rejected: %v", err)
	}
}
