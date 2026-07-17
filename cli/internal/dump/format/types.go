package format

// VaultDocument is the format-neutral snapshot used by Markdown writers.
type VaultDocument struct {
	Version       int
	ExportedAt    string
	Notes         []VaultNote
	Buffers       []VaultBuffer
	Tags          []VaultTag
	NoteTags      []VaultNoteTag
	RelationTypes []VaultRelationType
	Links         []VaultLink
}

type VaultNote struct {
	ID, Title, Content, CreatedAt, UpdatedAt            string
	Summary                                             *string
	Tags                                                []string
	Synced                                              bool
	SyncStatus                                          string
	SyncAttempts                                        int
	SyncLastError, SyncLastAttemptAt, SyncLastSuccessAt *string
	Links                                               []ResolvedLink
}

type VaultBuffer struct {
	ID, Content, CreatedAt, UpdatedAt string
	ProcessedAt                       *string
	Meta                              map[string]any
	Processed                         bool
}

type VaultTag struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	CreatedAt string `json:"created_at"`
}
type VaultNoteTag struct {
	NoteID    string `json:"note_id"`
	TagID     string `json:"tag_id"`
	CreatedAt string `json:"created_at"`
}
type VaultRelationType struct {
	ID              string  `json:"id"`
	Name            string  `json:"name"`
	Description     *string `json:"description"`
	CreatedAt       string  `json:"created_at"`
	IsBidirectional bool    `json:"is_bidirectional"`
}

type VaultLink struct {
	ID             string  `json:"id"`
	SourceID       string  `json:"source_id"`
	TargetID       string  `json:"target_id"`
	RelationTypeID string  `json:"relation_type_id"`
	Description    *string `json:"description"`
	CreatedAt      string  `json:"created_at"`
}

// ResolvedLink has target and relation display values pre-resolved.
type ResolvedLink struct {
	ID, TargetID, TargetTitle, RelationTypeID, RelationType, CreatedAt string
	Description                                                        *string
}
