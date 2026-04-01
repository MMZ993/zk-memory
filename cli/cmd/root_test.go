package cmd

import (
	"strings"
	"testing"
)

func TestFormatFatalMessageIncludesErrorPrefix(t *testing.T) {
	msg := formatFatalMessage("boom: %s", "bad")
	if msg != "error: boom: bad\n" {
		t.Fatalf("unexpected fatal message: %q", msg)
	}
}

func TestRenderRawJSONReturnsDecodeErrorForInvalidJSONInPrettyMode(t *testing.T) {
	if _, err := renderRawJSON([]byte("not-json"), true); err == nil {
		t.Fatal("expected decode error for invalid raw JSON")
	}
}

func TestRenderJSONCompactAndPretty(t *testing.T) {
	compact, err := renderJSON(map[string]string{"k": "v"}, false)
	if err != nil {
		t.Fatalf("compact render failed: %v", err)
	}
	if string(compact) != "{\"k\":\"v\"}" {
		t.Fatalf("unexpected compact output: %q", string(compact))
	}

	prettyJSON, err := renderJSON(map[string]string{"k": "v"}, true)
	if err != nil {
		t.Fatalf("pretty render failed: %v", err)
	}
	if !strings.Contains(string(prettyJSON), "\n") {
		t.Fatalf("expected pretty output to include newlines, got %q", string(prettyJSON))
	}
}
