package cmd

import "testing"

func TestParseSinceAcceptsSupportedFormats(t *testing.T) {
	inputs := []string{
		"2026-03-01",
		"2026-03-01T10:00:00",
		"2026-03-01T10:00:00Z",
	}

	for _, input := range inputs {
		t.Run(input, func(t *testing.T) {
			if _, err := parseSince(input); err != nil {
				t.Fatalf("expected parseSince(%q) to succeed, got %v", input, err)
			}
		})
	}
}

func TestParseSinceRejectsInvalidFormat(t *testing.T) {
	if _, err := parseSince("03/01/2026"); err == nil {
		t.Fatal("expected parseSince to reject invalid format")
	}
}
