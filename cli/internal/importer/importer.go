package importer

import (
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

type document struct {
	Version       int               `json:"version"`
	ExportedAt    string            `json:"exported_at"`
	Notes         []map[string]any  `json:"notes"`
	Tags          []json.RawMessage `json:"tags"`
	NoteTags      []json.RawMessage `json:"note_tags"`
	RelationTypes []json.RawMessage `json:"relation_types"`
	Links         []json.RawMessage `json:"links"`
	BufferNotes   []map[string]any  `json:"buffer_notes"`
}

type manifest struct {
	Version       int               `json:"version"`
	Tags          []json.RawMessage `json:"tags"`
	NoteTags      []json.RawMessage `json:"note_tags"`
	RelationTypes []json.RawMessage `json:"relation_types"`
	Links         []json.RawMessage `json:"links"`
}

// Load reconstructs a canonical import document from a generated vault or note file.
func Load(path string) (json.RawMessage, error) {
	info, err := os.Lstat(path)
	if err != nil {
		return nil, fmt.Errorf("inspect import path: %w", err)
	}
	if info.Mode()&os.ModeSymlink != 0 {
		return nil, fmt.Errorf("import path must not be a symlink")
	}
	if !info.IsDir() {
		if !info.Mode().IsRegular() {
			return nil, fmt.Errorf("import path must be a regular file or directory")
		}
		note, err := loadNoteFile(path)
		if err != nil {
			return nil, err
		}
		links, err := loadProjectedLinks(path, note["id"].(string))
		if err != nil {
			return nil, err
		}
		tags, noteTags := projectedTags(note)
		return marshalDocument(document{
			Version: 1, ExportedAt: time.Now().UTC().Format(time.RFC3339Nano),
			Notes: []map[string]any{note}, Tags: tags,
			NoteTags: noteTags, RelationTypes: []json.RawMessage{},
			Links: links, BufferNotes: []map[string]any{},
		})
	}

	manifestPath := filepath.Join(path, "zk-memory-manifest.json")
	manifestInfo, err := os.Lstat(manifestPath)
	if err != nil {
		return nil, fmt.Errorf("inspect zk-memory-manifest.json: %w", err)
	}
	if manifestInfo.Mode()&os.ModeSymlink != 0 || !manifestInfo.Mode().IsRegular() {
		return nil, fmt.Errorf("zk-memory-manifest.json must be a regular non-symlink file")
	}
	manifestData, err := os.ReadFile(manifestPath)
	if err != nil {
		return nil, fmt.Errorf("read zk-memory-manifest.json: %w", err)
	}
	var shared manifest
	if err := json.Unmarshal(manifestData, &shared); err != nil {
		return nil, fmt.Errorf("decode zk-memory-manifest.json: %w", err)
	}
	if shared.Version != 1 {
		return nil, fmt.Errorf("unsupported manifest version %d", shared.Version)
	}
	doc := document{
		Version: 1, ExportedAt: time.Now().UTC().Format(time.RFC3339Nano),
		Notes: []map[string]any{}, Tags: shared.Tags, NoteTags: shared.NoteTags,
		RelationTypes: shared.RelationTypes, Links: shared.Links,
		BufferNotes: []map[string]any{},
	}
	entries, err := os.ReadDir(path)
	if err != nil {
		return nil, fmt.Errorf("read vault: %w", err)
	}
	for _, entry := range entries {
		if entry.Type()&os.ModeSymlink != 0 {
			return nil, fmt.Errorf("vault contains symlink %s", entry.Name())
		}
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".md" {
			continue
		}
		entryInfo, err := entry.Info()
		if err != nil {
			return nil, fmt.Errorf("inspect vault entry %s: %w", entry.Name(), err)
		}
		if !entryInfo.Mode().IsRegular() {
			return nil, fmt.Errorf("vault Markdown entry %s must be regular", entry.Name())
		}
		note, err := loadNoteFile(filepath.Join(path, entry.Name()))
		if err != nil {
			return nil, err
		}
		if note["id"] != strings.TrimSuffix(entry.Name(), ".md") {
			return nil, fmt.Errorf("note ID does not match filename %s", entry.Name())
		}
		doc.Notes = append(doc.Notes, note)
	}
	bufferDir := filepath.Join(path, "buffer")
	bufferInfo, bufferInfoErr := os.Lstat(bufferDir)
	if bufferInfoErr == nil {
		if bufferInfo.Mode()&os.ModeSymlink != 0 || !bufferInfo.IsDir() {
			return nil, fmt.Errorf("buffer path must be a non-symlink directory")
		}
		bufferEntries, err := os.ReadDir(bufferDir)
		if err != nil {
			return nil, fmt.Errorf("read buffer directory: %w", err)
		}
		for _, entry := range bufferEntries {
			if entry.Type()&os.ModeSymlink != 0 || entry.IsDir() {
				return nil, fmt.Errorf("unsafe buffer entry %s", entry.Name())
			}
			if filepath.Ext(entry.Name()) != ".md" {
				continue
			}
			entryInfo, err := entry.Info()
			if err != nil {
				return nil, fmt.Errorf("inspect buffer entry %s: %w", entry.Name(), err)
			}
			if !entryInfo.Mode().IsRegular() {
				return nil, fmt.Errorf("buffer Markdown entry %s must be regular", entry.Name())
			}
			buffer, err := loadBufferFile(filepath.Join(bufferDir, entry.Name()))
			if err != nil {
				return nil, err
			}
			if buffer["id"] != strings.TrimSuffix(entry.Name(), ".md") {
				return nil, fmt.Errorf("buffer ID does not match filename %s", entry.Name())
			}
			doc.BufferNotes = append(doc.BufferNotes, buffer)
		}
	} else if !os.IsNotExist(bufferInfoErr) {
		return nil, fmt.Errorf("inspect buffer directory: %w", bufferInfoErr)
	}
	return marshalDocument(doc)
}

func projectedTags(note map[string]any) ([]json.RawMessage, []json.RawMessage) {
	tags := []json.RawMessage{}
	associations := []json.RawMessage{}
	for _, name := range note["tags"].([]string) {
		id := stableTagID(strings.TrimSpace(strings.ToLower(name)))
		tag, _ := json.Marshal(map[string]any{
			"id": id, "name": name, "created_at": note["created_at"],
		})
		association, _ := json.Marshal(map[string]any{
			"note_id": note["id"], "tag_id": id, "created_at": note["created_at"],
		})
		tags = append(tags, tag)
		associations = append(associations, association)
	}
	return tags, associations
}

func stableTagID(name string) string {
	sum := sha256.Sum256([]byte("zk-memory-markdown-tag:" + name))
	// Set RFC 4122 variant/version bits for a deterministic UUID-shaped ID.
	sum[6] = (sum[6] & 0x0f) | 0x50
	sum[8] = (sum[8] & 0x3f) | 0x80
	hex := fmt.Sprintf("%x", sum[:16])
	return hex[0:8] + "-" + hex[8:12] + "-" + hex[12:16] + "-" + hex[16:20] + "-" + hex[20:32]
}

type projectedLink struct {
	ID             string  `json:"ID"`
	TargetID       string  `json:"TargetID"`
	RelationTypeID string  `json:"RelationTypeID"`
	RelationType   string  `json:"RelationType"`
	CreatedAt      string  `json:"CreatedAt"`
	Description    *string `json:"Description"`
}

func loadProjectedLinks(path, sourceID string) ([]json.RawMessage, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read %s: %w", path, err)
	}
	links := []json.RawMessage{}
	const marker = "<!-- zk-memory-link-base64: "
	for _, line := range strings.Split(string(data), "\n") {
		start := strings.Index(line, marker)
		if start < 0 {
			continue
		}
		encoded := line[start+len(marker):]
		encoded = strings.TrimSuffix(encoded, " -->")
		decoded, err := base64.StdEncoding.DecodeString(encoded)
		if err != nil {
			return nil, fmt.Errorf("decode link metadata in %s: %w", path, err)
		}
		var item projectedLink
		if err := json.Unmarshal(decoded, &item); err != nil {
			return nil, fmt.Errorf("decode link metadata in %s: %w", path, err)
		}
		link, _ := json.Marshal(map[string]any{
			"id": item.ID, "source_id": sourceID, "target_id": item.TargetID,
			"relation_type_id": item.RelationTypeID, "description": item.Description,
			"created_at": item.CreatedAt,
		})
		links = append(links, link)
	}
	return links, nil
}

func loadNoteFile(path string) (map[string]any, error) {
	fields, body, err := parseMarkdown(path)
	if err != nil {
		return nil, err
	}
	if fields["zk_memory_version"] != "1" || fields["type"] == "buffer" {
		return nil, fmt.Errorf("%s is not a generated note", path)
	}
	attempts, err := strconv.Atoi(fields["sync_attempts"])
	if err != nil {
		return nil, fmt.Errorf("invalid sync_attempts in %s", path)
	}
	note := map[string]any{
		"id": scalar(fields["id"]), "title": scalar(fields["title"]),
		"content": stripProjection(body), "summary": nullable(fields["summary"]),
		"tags": parseTags(fields["tags"]), "synced": fields["synced"] == "true",
		"sync_status": scalar(fields["sync_status"]), "sync_attempts": attempts,
		"sync_last_error":      nullable(fields["sync_last_error"]),
		"sync_last_attempt_at": nullable(fields["sync_last_attempt_at"]),
		"sync_last_success_at": nullable(fields["sync_last_success_at"]),
		"created_at":           scalar(fields["created_at"]), "updated_at": scalar(fields["updated_at"]),
	}
	return note, nil
}

func loadBufferFile(path string) (map[string]any, error) {
	fields, body, err := parseMarkdown(path)
	if err != nil {
		return nil, err
	}
	if fields["type"] != "buffer" {
		return nil, fmt.Errorf("%s is not a buffer file", path)
	}
	var meta any
	metaText := strings.Trim(fields["meta_json"], "'")
	metaText = strings.ReplaceAll(metaText, "''", "'")
	if err := json.Unmarshal([]byte(metaText), &meta); err != nil {
		return nil, fmt.Errorf("decode buffer metadata in %s: %w", path, err)
	}
	return map[string]any{
		"id": scalar(fields["id"]), "content": body, "meta": meta,
		"processed":    fields["processed"] == "true",
		"processed_at": nullable(fields["processed_at"]),
		"created_at":   scalar(fields["created_at"]), "updated_at": scalar(fields["updated_at"]),
	}, nil
}

func parseMarkdown(path string) (map[string]string, string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, "", fmt.Errorf("read %s: %w", path, err)
	}
	text := string(data)
	if !strings.HasPrefix(text, "---\n") {
		return nil, "", fmt.Errorf("missing frontmatter in %s", path)
	}
	end := strings.Index(text[4:], "\n---\n")
	if end < 0 {
		return nil, "", fmt.Errorf("unterminated frontmatter in %s", path)
	}
	front := text[4 : 4+end]
	body := text[4+end+5:]
	if strings.HasPrefix(body, "\n") {
		body = body[1:]
	}
	fields := map[string]string{}
	lines := strings.Split(front, "\n")
	for i := 0; i < len(lines); i++ {
		line := lines[i]
		key, value, ok := strings.Cut(line, ":")
		if !ok {
			return nil, "", fmt.Errorf("invalid frontmatter in %s", path)
		}
		value = strings.TrimSpace(value)
		if key == "tags" && value == "" {
			var tags []string
			for i+1 < len(lines) && strings.HasPrefix(lines[i+1], "  - ") {
				i++
				tags = append(tags, strings.TrimSpace(strings.TrimPrefix(lines[i], "  - ")))
			}
			fields[key] = strings.Join(tags, "\x00")
			continue
		}
		fields[key] = value
	}
	return fields, body, nil
}

func parseTags(value string) []string {
	if value == "[]" || value == "" {
		return []string{}
	}
	parts := strings.Split(value, "\x00")
	for i := range parts {
		parts[i] = scalar(parts[i])
	}
	return parts
}

func scalar(value string) string {
	if unquoted, err := strconv.Unquote(value); err == nil {
		return unquoted
	}
	return value
}

func nullable(value string) any {
	if value == "null" || value == "" {
		return nil
	}
	return scalar(value)
}

func stripProjection(body string) string {
	markers := [][2]string{
		{"\n\n<!-- zk-memory:links:start -->", "<!-- zk-memory:links:end -->"},
		{"\n\n<!-- zk-memory:related:start -->", "<!-- zk-memory:related:end -->"},
	}
	for _, pair := range markers {
		start := strings.LastIndex(body, pair[0])
		if start < 0 {
			continue
		}
		end := strings.Index(body[start+len(pair[0]):], pair[1])
		if end < 0 {
			continue
		}
		tail := body[start+len(pair[0])+end+len(pair[1]):]
		if strings.TrimSpace(tail) == "" {
			return body[:start]
		}
	}
	return body
}

func marshalDocument(doc document) (json.RawMessage, error) {
	data, err := json.Marshal(doc)
	if err != nil {
		return nil, fmt.Errorf("encode import document: %w", err)
	}
	return data, nil
}
