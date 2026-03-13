package format

// EnrichedNote is a note with resolved links, passed to format writers.
type EnrichedNote struct {
	ID        string
	Title     string
	Content   string
	Summary   string
	Tags      []string
	CreatedAt string
	UpdatedAt string
	Synced    bool
	Links     []ResolvedLink
}

// ResolvedLink has target title and relation type name pre-resolved.
type ResolvedLink struct {
	ID           string
	TargetID     string
	TargetTitle  string
	RelationType string
	Description  string
}
