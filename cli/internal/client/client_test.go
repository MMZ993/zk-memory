package client_test

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"agents-memory-cli/internal/client"
)

// ── Constructor error cases ───────────────────────────────────────────────────

func TestNew_MissingURL(t *testing.T) {
	t.Setenv("MEMORY_API_URL", "")
	t.Setenv("MEMORY_API_KEY", "")
	t.Setenv("MEMORY_TIMEOUT", "")
	_, err := client.New()
	if err == nil {
		t.Fatal("expected error when MEMORY_API_URL is empty")
	}
}

func TestNew_InvalidTimeout(t *testing.T) {
	t.Setenv("MEMORY_API_URL", "http://localhost:9999")
	t.Setenv("MEMORY_API_KEY", "")
	t.Setenv("MEMORY_TIMEOUT", "not-a-number")
	_, err := client.New()
	if err == nil {
		t.Fatal("expected error for non-numeric MEMORY_TIMEOUT")
	}
}

func TestNew_ValidTimeout(t *testing.T) {
	t.Setenv("MEMORY_API_URL", "http://localhost:9999")
	t.Setenv("MEMORY_API_KEY", "")
	t.Setenv("MEMORY_TIMEOUT", "60")
	_, err := client.New()
	if err != nil {
		t.Fatalf("expected success for valid MEMORY_TIMEOUT, got: %v", err)
	}
}

// ── Auth header behaviour ─────────────────────────────────────────────────────

// emptyNotesHandler returns an httptest handler that captures the incoming
// X-Api-Key header and responds with an empty JSON array (valid ListNotes response).
func emptyNotesHandler(captured *string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		*captured = r.Header.Get("X-Api-Key")
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode([]any{}) //nolint:errcheck
	}
}

func TestDo_SendsAPIKeyHeader(t *testing.T) {
	var captured string
	srv := httptest.NewServer(emptyNotesHandler(&captured))
	defer srv.Close()

	t.Setenv("MEMORY_API_URL", srv.URL)
	t.Setenv("MEMORY_API_KEY", "my-test-key")
	t.Setenv("MEMORY_TIMEOUT", "")

	c, err := client.New()
	if err != nil {
		t.Fatalf("New(): %v", err)
	}
	_, _ = c.ListNotes(client.ListOpts{})
	if captured != "my-test-key" {
		t.Errorf("X-Api-Key = %q, want %q", captured, "my-test-key")
	}
}

func TestDo_OmitsAPIKeyHeaderWhenNotSet(t *testing.T) {
	var captured string
	srv := httptest.NewServer(emptyNotesHandler(&captured))
	defer srv.Close()

	t.Setenv("MEMORY_API_URL", srv.URL)
	t.Setenv("MEMORY_API_KEY", "")
	t.Setenv("MEMORY_TIMEOUT", "")

	c, err := client.New()
	if err != nil {
		t.Fatalf("New(): %v", err)
	}
	_, _ = c.ListNotes(client.ListOpts{})
	if captured != "" {
		t.Errorf("X-Api-Key = %q, want empty string (no key should be sent)", captured)
	}
}

// ── HTTP error code mapping ───────────────────────────────────────────────────

func statusHandler(code int, body string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(code)
		w.Write([]byte(body)) //nolint:errcheck
	}
}

func assertAPIError(t *testing.T, err error, wantCode int) {
	t.Helper()
	if err == nil {
		t.Fatalf("expected error for HTTP %d, got nil", wantCode)
	}
	var apiErr *client.APIError
	if !errors.As(err, &apiErr) {
		t.Fatalf("expected *client.APIError, got %T: %v", err, err)
	}
	if apiErr.StatusCode != wantCode {
		t.Errorf("StatusCode = %d, want %d", apiErr.StatusCode, wantCode)
	}
}

func TestDo_Returns401AsAPIError(t *testing.T) {
	srv := httptest.NewServer(statusHandler(
		http.StatusUnauthorized,
		`{"detail":"API key required"}`,
	))
	defer srv.Close()

	t.Setenv("MEMORY_API_URL", srv.URL)
	t.Setenv("MEMORY_API_KEY", "")
	t.Setenv("MEMORY_TIMEOUT", "")

	c, err := client.New()
	if err != nil {
		t.Fatalf("New(): %v", err)
	}
	_, err = c.ListNotes(client.ListOpts{})
	assertAPIError(t, err, 401)
}

func TestDo_Returns403AsAPIError(t *testing.T) {
	srv := httptest.NewServer(statusHandler(
		http.StatusForbidden,
		`{"detail":"API key does not have the required scope for this operation"}`,
	))
	defer srv.Close()

	t.Setenv("MEMORY_API_URL", srv.URL)
	t.Setenv("MEMORY_API_KEY", "read-only-key")
	t.Setenv("MEMORY_TIMEOUT", "")

	c, err := client.New()
	if err != nil {
		t.Fatalf("New(): %v", err)
	}
	_, err = c.ListNotes(client.ListOpts{})
	assertAPIError(t, err, 403)
}

func TestDo_Returns404AsAPIError(t *testing.T) {
	srv := httptest.NewServer(statusHandler(
		http.StatusNotFound,
		`{"detail":"Not Found"}`,
	))
	defer srv.Close()

	t.Setenv("MEMORY_API_URL", srv.URL)
	t.Setenv("MEMORY_API_KEY", "some-key")
	t.Setenv("MEMORY_TIMEOUT", "")

	c, err := client.New()
	if err != nil {
		t.Fatalf("New(): %v", err)
	}
	_, err = c.GetNote("nonexistent-id")
	assertAPIError(t, err, 404)
}

// ── Successful response ───────────────────────────────────────────────────────

func TestDo_SuccessfulResponse(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`[{"id":"abc","title":"Hello","content":"World","tags":[],"links":[],"synced":true,"created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z"}]`)) //nolint:errcheck
	}))
	defer srv.Close()

	t.Setenv("MEMORY_API_URL", srv.URL)
	t.Setenv("MEMORY_API_KEY", "")
	t.Setenv("MEMORY_TIMEOUT", "")

	c, err := client.New()
	if err != nil {
		t.Fatalf("New(): %v", err)
	}
	notes, err := c.ListNotes(client.ListOpts{})
	if err != nil {
		t.Fatalf("ListNotes(): %v", err)
	}
	if len(notes) != 1 {
		t.Fatalf("len(notes) = %d, want 1", len(notes))
	}
	if notes[0].ID != "abc" {
		t.Errorf("notes[0].ID = %q, want %q", notes[0].ID, "abc")
	}
}
