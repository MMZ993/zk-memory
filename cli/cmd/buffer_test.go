package cmd

import (
	"bytes"
	"strings"
	"testing"

	"agents-memory-cli/internal/client"
)

func TestResolveProcessedFilterErrorsWhenBothFlagsSet(t *testing.T) {
	if _, err := resolveProcessedFilter(true, true, false); err == nil {
		t.Fatal("expected error when both --processed and --unprocessed are set")
	}
}

func TestBuildBufferListOptsReturnsValidationError(t *testing.T) {
	if _, err := buildBufferListOpts(true, true, false, 10, 20); err == nil {
		t.Fatal("expected mutual-exclusion validation error")
	}
}

func TestResolveProcessedFilterDefaultsToUnprocessed(t *testing.T) {
	processed, err := resolveProcessedFilter(false, false, false)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if processed == nil || *processed {
		t.Fatalf("expected default filter to be processed=false, got %#v", processed)
	}
}

func TestResolveProcessedFilterReturnsProcessedForProcessedFlag(t *testing.T) {
	processed, err := resolveProcessedFilter(true, false, false)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if processed == nil || !*processed {
		t.Fatalf("expected processed filter to be true, got %#v", processed)
	}
}

func TestResolveProcessedFilterAllReturnsNoFilter(t *testing.T) {
	processed, err := resolveProcessedFilter(false, false, true)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if processed != nil {
		t.Fatalf("expected no filter for --all, got %#v", processed)
	}
}

func TestBufferListCommandValidatesFlagsBeforeClientSetup(t *testing.T) {
	origClientFactory := newBufferClient
	origExit := exitFn
	origStderr := stderrWriter
	origProcessed := bufferListProcessed
	origUnprocessed := bufferListUnprocessed
	origAll := bufferListAll
	defer func() {
		newBufferClient = origClientFactory
		exitFn = origExit
		stderrWriter = origStderr
		bufferListProcessed = origProcessed
		bufferListUnprocessed = origUnprocessed
		bufferListAll = origAll
	}()

	called := 0
	newBufferClient = func() (*client.Client, error) {
		called++
		return nil, nil
	}

	var stderr bytes.Buffer
	stderrWriter = &stderr
	exitFn = func(code int) {
		panic(code)
	}

	bufferListProcessed = true
	bufferListUnprocessed = true

	defer func() {
		recovered := recover()
		if recovered == nil {
			t.Fatal("expected fatal exit")
		}
		exitCode, ok := recovered.(int)
		if !ok || exitCode != 1 {
			t.Fatalf("expected exit code 1, got %#v", recovered)
		}
		if called != 0 {
			t.Fatalf("expected client factory to be skipped, called=%d", called)
		}
		if !strings.Contains(stderr.String(), "mutually exclusive") {
			t.Fatalf("unexpected stderr output: %q", stderr.String())
		}
	}()

	bufferListCmd.Run(bufferListCmd, nil)
}
