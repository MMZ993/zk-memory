package dump

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"agents-memory-cli/internal/client"
	"agents-memory-cli/internal/dump/format"
)

type Config struct {
	OutputDir      string
	Format         string
	Since          time.Time
	StatePath      string
	NoState, Force bool
}

type exportDocument struct {
	Version       int              `json:"version"`
	ExportedAt    string           `json:"exported_at"`
	Notes         []exportNote     `json:"notes"`
	Tags          []exportTag      `json:"tags"`
	NoteTags      []exportNoteTag  `json:"note_tags"`
	RelationTypes []exportRelation `json:"relation_types"`
	Links         []exportLink     `json:"links"`
	Buffers       []exportBuffer   `json:"buffer_notes"`
}
type exportNote struct {
	ID, Title, Content string
	Summary            *string
	Tags               []string
	Synced             bool
	SyncStatus         string  `json:"sync_status"`
	SyncAttempts       int     `json:"sync_attempts"`
	SyncLastError      *string `json:"sync_last_error"`
	SyncLastAttemptAt  *string `json:"sync_last_attempt_at"`
	SyncLastSuccessAt  *string `json:"sync_last_success_at"`
	CreatedAt          string  `json:"created_at"`
	UpdatedAt          string  `json:"updated_at"`
}
type exportTag struct {
	ID, Name  string
	CreatedAt string `json:"created_at"`
}
type exportNoteTag struct {
	NoteID    string `json:"note_id"`
	TagID     string `json:"tag_id"`
	CreatedAt string `json:"created_at"`
}
type exportRelation struct {
	ID, Name        string
	Description     *string
	IsBidirectional bool   `json:"is_bidirectional"`
	CreatedAt       string `json:"created_at"`
}
type exportLink struct {
	ID             string
	SourceID       string `json:"source_id"`
	TargetID       string `json:"target_id"`
	RelationTypeID string `json:"relation_type_id"`
	Description    *string
	CreatedAt      string `json:"created_at"`
}
type exportBuffer struct {
	ID, Content string
	Meta        map[string]any
	Processed   bool
	ProcessedAt *string `json:"processed_at"`
	CreatedAt   string  `json:"created_at"`
	UpdatedAt   string  `json:"updated_at"`
}

func Run(c *client.Client, cfg Config) (*DumpStats, error) {
	if cfg.StatePath == "" {
		cfg.StatePath = filepath.Join(cfg.OutputDir, ".dump-state.json")
	}
	var previous *State
	if !cfg.NoState {
		var err error
		previous, err = ReadState(cfg.StatePath)
		if err != nil {
			return nil, fmt.Errorf("read state file: %w", err)
		}
		if previous != nil && previous.Format != cfg.Format {
			if !cfg.Force {
				return nil, fmt.Errorf("output directory was last dumped as %q, requested format is %q\nuse --force to overwrite, or choose a different --output directory", previous.Format, cfg.Format)
			}
			previous = nil // Do not delete files managed by the previous format.
		}
	}
	if err := os.MkdirAll(cfg.OutputDir, 0755); err != nil {
		return nil, fmt.Errorf("create output dir: %w", err)
	}
	raw, err := c.ExportAll()
	if err != nil {
		return nil, fmt.Errorf("fetch full export: %w", err)
	}
	if err := validateExportDocument(raw); err != nil {
		return nil, err
	}
	var doc exportDocument
	if err := json.Unmarshal(raw, &doc); err != nil {
		return nil, fmt.Errorf("parse full export: %w", err)
	}
	if err := validateExportRecords(doc); err != nil {
		return nil, err
	}
	stats := DumpStats{NotesTotal: len(doc.Notes), Links: len(doc.Links), Tags: len(doc.Tags)}
	if cfg.Format == "json" {
		if err := format.WriteJSON(raw, cfg.OutputDir); err != nil {
			return nil, err
		}
		stats.NotesDumped = len(doc.Notes)
		return finishState(cfg, stats, nil)
	}
	vault := toVaultDocument(doc)
	var files map[string][]byte
	switch cfg.Format {
	case "obsidian":
		files, err = format.RenderObsidian(vault)
	case "wikijs":
		files, err = format.RenderWikiJS(vault)
	default:
		return nil, fmt.Errorf("unknown format: %q", cfg.Format)
	}
	if err != nil {
		return nil, err
	}
	hashes := make(map[string]string, len(files))
	for path, content := range files {
		hash := contentHash(content)
		hashes[path] = hash
		fullPath, err := safeOutputPath(cfg.OutputDir, path)
		if err != nil {
			return nil, err
		}
		if previous != nil && previous.Files[path] == hash {
			if existing, readErr := os.ReadFile(fullPath); readErr == nil && contentHash(existing) == hash {
				continue
			}
		}
		if err := os.MkdirAll(filepath.Dir(fullPath), 0755); err != nil {
			return nil, fmt.Errorf("create output directory: %w", err)
		}
		if err := os.WriteFile(fullPath, content, 0644); err != nil {
			return nil, fmt.Errorf("write %s: %w", fullPath, err)
		}
		if filepath.Ext(path) == ".md" && filepath.Dir(path) == "." {
			stats.NotesDumped++
		}
	}
	if previous != nil {
		for path := range previous.Files {
			if _, exists := hashes[path]; exists {
				continue
			}
			fullPath, pathErr := safeOutputPath(cfg.OutputDir, path)
			if pathErr != nil {
				return nil, pathErr
			}
			managed, checkErr := isManagedStaleFile(fullPath, path)
			if checkErr != nil {
				return nil, checkErr
			}
			if !managed {
				return nil, fmt.Errorf("refuse to remove unrecognized managed file %q", path)
			}
			if err := os.Remove(fullPath); err != nil && !os.IsNotExist(err) {
				return nil, fmt.Errorf("remove stale %s: %w", path, err)
			}
		}
	}
	return finishState(cfg, stats, hashes)
}

func isManagedStaleFile(fullPath, relative string) (bool, error) {
	if relative == "zk-memory-manifest.json" {
		return true, nil
	}
	if filepath.Ext(relative) != ".md" || (filepath.Dir(relative) != "." && filepath.ToSlash(filepath.Dir(relative)) != "buffer") {
		return false, nil
	}
	info, err := os.Lstat(fullPath)
	if os.IsNotExist(err) {
		return true, nil
	}
	if err != nil {
		return false, err
	}
	if !info.Mode().IsRegular() {
		return false, nil
	}
	data, err := os.ReadFile(fullPath)
	if err != nil {
		return false, err
	}
	id := filepath.Base(relative)
	id = id[:len(id)-len(filepath.Ext(id))]
	return bytes.Contains(data, []byte("zk_memory_version: 1\n")) && bytes.Contains(data, []byte("id: \""+id+"\"\n")), nil
}

func validateExportDocument(raw json.RawMessage) error {
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(raw, &fields); err != nil {
		return fmt.Errorf("parse full export: %w", err)
	}
	var version int
	if err := json.Unmarshal(fields["version"], &version); err != nil || version != 1 {
		return fmt.Errorf("unsupported export version: expected 1")
	}
	if exportedAt := fields["exported_at"]; len(exportedAt) == 0 || string(exportedAt) == "null" {
		return fmt.Errorf("full export missing exported_at")
	}
	for _, name := range []string{"notes", "tags", "note_tags", "relation_types", "links", "buffer_notes"} {
		value, ok := fields[name]
		if !ok || string(value) == "null" {
			return fmt.Errorf("full export missing collection %q", name)
		}
		var collection []json.RawMessage
		if err := json.Unmarshal(value, &collection); err != nil {
			return fmt.Errorf("full export collection %q is invalid: %w", name, err)
		}
	}
	return nil
}

func validateExportRecords(doc exportDocument) error {
	notes, tags, relations := map[string]bool{}, map[string]bool{}, map[string]bool{}
	for _, note := range doc.Notes {
		if note.ID == "" {
			return fmt.Errorf("full export contains note without ID")
		}
		if notes[note.ID] {
			return fmt.Errorf("full export contains duplicate note ID %q", note.ID)
		}
		notes[note.ID] = true
	}
	for _, tag := range doc.Tags {
		if tag.ID == "" {
			return fmt.Errorf("full export contains tag without ID")
		}
		if tags[tag.ID] {
			return fmt.Errorf("full export contains duplicate tag ID %q", tag.ID)
		}
		tags[tag.ID] = true
	}
	for _, relation := range doc.RelationTypes {
		if relation.ID == "" {
			return fmt.Errorf("full export contains relation type without ID")
		}
		if relations[relation.ID] {
			return fmt.Errorf("full export contains duplicate relation type ID %q", relation.ID)
		}
		relations[relation.ID] = true
	}
	// Legacy databases may contain orphaned associations. Preserve references
	// to missing rows, while still rejecting malformed or duplicate records.
	noteTagPairs := map[string]bool{}
	for _, noteTag := range doc.NoteTags {
		if noteTag.NoteID == "" || noteTag.TagID == "" {
			return fmt.Errorf("full export contains note-tag association without IDs")
		}
		pair := noteTag.NoteID + "\x00" + noteTag.TagID
		if noteTagPairs[pair] {
			return fmt.Errorf("full export contains duplicate note-tag association")
		}
		noteTagPairs[pair] = true
	}
	linkIDs, bufferIDs := map[string]bool{}, map[string]bool{}
	for _, link := range doc.Links {
		if link.ID == "" || link.SourceID == "" || link.TargetID == "" || link.RelationTypeID == "" || linkIDs[link.ID] {
			return fmt.Errorf("full export contains invalid or duplicate link")
		}
		linkIDs[link.ID] = true
	}
	for _, buffer := range doc.Buffers {
		if buffer.ID == "" || bufferIDs[buffer.ID] {
			return fmt.Errorf("full export contains invalid or duplicate buffer ID")
		}
		bufferIDs[buffer.ID] = true
	}
	return nil
}

func finishState(cfg Config, stats DumpStats, files map[string]string) (*DumpStats, error) {
	if !cfg.NoState {
		state := State{DumpedAt: time.Now().UTC().Format(time.RFC3339), Format: cfg.Format, Stats: stats, Files: files}
		if err := WriteState(cfg.StatePath, state); err != nil {
			return nil, fmt.Errorf("write state file: %w", err)
		}
	}
	return &stats, nil
}
func safeOutputPath(outputDir, relative string) (string, error) {
	if relative == "" || filepath.IsAbs(relative) {
		return "", fmt.Errorf("unsafe managed path %q", relative)
	}
	root, err := filepath.Abs(outputDir)
	if err != nil {
		return "", fmt.Errorf("resolve output directory: %w", err)
	}
	candidate := filepath.Join(root, filepath.FromSlash(relative))
	if !isWithin(root, candidate) {
		return "", fmt.Errorf("unsafe managed path %q", relative)
	}
	resolvedRoot, err := filepath.EvalSymlinks(root)
	if err != nil {
		return "", fmt.Errorf("resolve output directory: %w", err)
	}
	if resolvedParent, evalErr := filepath.EvalSymlinks(filepath.Dir(candidate)); evalErr == nil && resolvedParent != resolvedRoot && !isWithin(resolvedRoot, resolvedParent) {
		return "", fmt.Errorf("unsafe managed path %q", relative)
	}
	if info, statErr := os.Lstat(candidate); statErr == nil && info.Mode()&os.ModeSymlink != 0 {
		return "", fmt.Errorf("unsafe managed symlink %q", relative)
	}
	return candidate, nil
}

func isWithin(root, candidate string) bool {
	rel, err := filepath.Rel(root, candidate)
	return err == nil && rel != ".." && rel != "." && !(len(rel) >= 3 && rel[:3] == ".."+string(filepath.Separator))
}

func contentHash(content []byte) string {
	sum := sha256.Sum256(content)
	return hex.EncodeToString(sum[:])
}

func toVaultDocument(doc exportDocument) format.VaultDocument {
	out := format.VaultDocument{Version: doc.Version, ExportedAt: doc.ExportedAt}
	titles := map[string]string{}
	relations := map[string]string{}
	for _, n := range doc.Notes {
		titles[n.ID] = n.Title
	}
	for _, r := range doc.RelationTypes {
		relations[r.ID] = r.Name
		out.RelationTypes = append(out.RelationTypes, format.VaultRelationType{ID: r.ID, Name: r.Name, Description: r.Description, IsBidirectional: r.IsBidirectional, CreatedAt: r.CreatedAt})
	}
	links := map[string][]format.ResolvedLink{}
	for _, l := range doc.Links {
		out.Links = append(out.Links, format.VaultLink{ID: l.ID, SourceID: l.SourceID, TargetID: l.TargetID, RelationTypeID: l.RelationTypeID, Description: l.Description, CreatedAt: l.CreatedAt})
		links[l.SourceID] = append(links[l.SourceID], format.ResolvedLink{ID: l.ID, TargetID: l.TargetID, TargetTitle: titles[l.TargetID], RelationTypeID: l.RelationTypeID, RelationType: relations[l.RelationTypeID], Description: l.Description, CreatedAt: l.CreatedAt})
	}
	for _, n := range doc.Notes {
		out.Notes = append(out.Notes, format.VaultNote{ID: n.ID, Title: n.Title, Content: n.Content, Summary: n.Summary, Tags: n.Tags, Synced: n.Synced, SyncStatus: n.SyncStatus, SyncAttempts: n.SyncAttempts, SyncLastError: n.SyncLastError, SyncLastAttemptAt: n.SyncLastAttemptAt, SyncLastSuccessAt: n.SyncLastSuccessAt, CreatedAt: n.CreatedAt, UpdatedAt: n.UpdatedAt, Links: links[n.ID]})
	}
	for _, b := range doc.Buffers {
		out.Buffers = append(out.Buffers, format.VaultBuffer{ID: b.ID, Content: b.Content, Meta: b.Meta, Processed: b.Processed, ProcessedAt: b.ProcessedAt, CreatedAt: b.CreatedAt, UpdatedAt: b.UpdatedAt})
	}
	for _, t := range doc.Tags {
		out.Tags = append(out.Tags, format.VaultTag{ID: t.ID, Name: t.Name, CreatedAt: t.CreatedAt})
	}
	for _, nt := range doc.NoteTags {
		out.NoteTags = append(out.NoteTags, format.VaultNoteTag{NoteID: nt.NoteID, TagID: nt.TagID, CreatedAt: nt.CreatedAt})
	}
	return out
}
