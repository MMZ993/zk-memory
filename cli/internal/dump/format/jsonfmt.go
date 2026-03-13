package format

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// jsonNote is the JSON representation of an enriched note.
type jsonNote struct {
	ID        string         `json:"id"`
	Title     string         `json:"title"`
	Content   string         `json:"content"`
	Summary   string         `json:"summary,omitempty"`
	Tags      []string       `json:"tags"`
	CreatedAt string         `json:"created_at"`
	UpdatedAt string         `json:"updated_at"`
	Synced    bool           `json:"synced"`
	Links     []jsonLink     `json:"links"`
}

type jsonLink struct {
	ID           string `json:"id"`
	TargetID     string `json:"target_id"`
	TargetTitle  string `json:"target_title"`
	RelationType string `json:"relation_type"`
	Description  string `json:"description,omitempty"`
}

// WriteJSON writes all notes to a single notes.json file in outDir.
func WriteJSON(notes []EnrichedNote, outDir string) error {
	out := make([]jsonNote, 0, len(notes))
	for _, n := range notes {
		jn := jsonNote{
			ID:        n.ID,
			Title:     n.Title,
			Content:   n.Content,
			Summary:   n.Summary,
			Tags:      n.Tags,
			CreatedAt: n.CreatedAt,
			UpdatedAt: n.UpdatedAt,
			Synced:    n.Synced,
		}
		if jn.Tags == nil {
			jn.Tags = []string{}
		}
		for _, lnk := range n.Links {
			jn.Links = append(jn.Links, jsonLink{
				ID:           lnk.ID,
				TargetID:     lnk.TargetID,
				TargetTitle:  lnk.TargetTitle,
				RelationType: lnk.RelationType,
				Description:  lnk.Description,
			})
		}
		if jn.Links == nil {
			jn.Links = []jsonLink{}
		}
		out = append(out, jn)
	}

	data, err := json.MarshalIndent(out, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal notes: %w", err)
	}

	path := filepath.Join(outDir, "notes.json")
	if err := os.WriteFile(path, data, 0644); err != nil {
		return fmt.Errorf("write %s: %w", path, err)
	}
	return nil
}
