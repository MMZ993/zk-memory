package cmd

import "testing"

func TestValidateNotesCreateInputRequiresTitleAndContent(t *testing.T) {
	tests := []struct {
		name    string
		title   string
		content string
		wantErr bool
	}{
		{name: "missing title", title: "", content: "body", wantErr: true},
		{name: "missing content", title: "title", content: "", wantErr: true},
		{name: "both present", title: "title", content: "body", wantErr: false},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			err := validateNotesCreateInput(tc.title, tc.content)
			if tc.wantErr && err == nil {
				t.Fatal("expected validation error")
			}
			if !tc.wantErr && err != nil {
				t.Fatalf("expected no validation error, got %v", err)
			}
		})
	}
}

func TestSplitTagsTrimsAndDropsEmptyValues(t *testing.T) {
	tags := splitTags(" alpha, ,beta ,  gamma  ,")
	if len(tags) != 3 {
		t.Fatalf("expected 3 tags, got %d", len(tags))
	}
	if tags[0] != "alpha" || tags[1] != "beta" || tags[2] != "gamma" {
		t.Fatalf("unexpected tags: %#v", tags)
	}
}

func TestSplitTagsOptReturnsNilForEmptyInput(t *testing.T) {
	tags := splitTagsOpt("")
	if tags != nil {
		t.Fatalf("expected nil tags, got %#v", tags)
	}
}

func TestNotesSearchCommandRequiresExactlyOneArg(t *testing.T) {
	if err := notesSearchCmd.Args(notesSearchCmd, []string{}); err == nil {
		t.Fatal("expected arg validation error for missing query")
	}
	if err := notesSearchCmd.Args(notesSearchCmd, []string{"q", "extra"}); err == nil {
		t.Fatal("expected arg validation error for extra query args")
	}
}

func TestNotesTagsAddCommandRequiresExactlyTwoArgs(t *testing.T) {
	if err := notesTagsAddCmd.Args(notesTagsAddCmd, []string{"note-id"}); err == nil {
		t.Fatal("expected arg validation error for missing tag name")
	}
	if err := notesTagsAddCmd.Args(notesTagsAddCmd, []string{"note-id", "tag", "extra"}); err == nil {
		t.Fatal("expected arg validation error for extra args")
	}
}

func TestTagsCreateCommandRequiresExactlyOneArg(t *testing.T) {
	if err := tagsCreateCmd.Args(tagsCreateCmd, []string{}); err == nil {
		t.Fatal("expected arg validation error for missing tag name")
	}
	if err := tagsCreateCmd.Args(tagsCreateCmd, []string{"tag", "extra"}); err == nil {
		t.Fatal("expected arg validation error for extra args")
	}
}
