package client_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"agents-memory-cli/internal/client"
)

func TestImportDocumentPostsModeAndSelection(t *testing.T) {
	var request map[string]any
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/import/" || r.Method != http.MethodPost {
			t.Fatalf("unexpected request: %s %s", r.Method, r.URL.Path)
		}
		if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			t.Fatal(err)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"mode":"soft","clean":true}`))
	}))
	defer srv.Close()
	t.Setenv("MEMORY_API_URL", srv.URL)
	t.Setenv("MEMORY_API_KEY", "admin")

	c, err := client.New()
	if err != nil {
		t.Fatal(err)
	}
	_, err = c.ImportDocument(json.RawMessage(`{"version":1}`), client.ImportOptions{
		Mode: "soft", EntityType: "notes", EntityID: "note-1",
	})
	if err != nil {
		t.Fatal(err)
	}
	selection := request["selection"].(map[string]any)
	if request["mode"] != "soft" || selection["type"] != "notes" || selection["id"] != "note-1" {
		t.Fatalf("unexpected request body: %#v", request)
	}
}
