from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.database import Link, Note, NoteTag, RelationType, Tag
from app.services.import_service import analyze_import, apply_import


NOW = datetime(2026, 7, 17, tzinfo=timezone.utc)


def _document(**overrides):
    document = {
        "version": 1,
        "exported_at": NOW.isoformat(),
        "notes": [],
        "tags": [],
        "note_tags": [],
        "relation_types": [],
        "links": [],
        "buffer_notes": [],
    }
    document.update(overrides)
    return document


def _note(note_id: str, *, title: str = "Imported"):
    return {
        "id": note_id,
        "title": title,
        "content": "body",
        "summary": None,
        "tags": ["extra"],
        "synced": False,
        "sync_status": "pending",
        "sync_attempts": 0,
        "sync_last_error": None,
        "sync_last_attempt_at": None,
        "sync_last_success_at": None,
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
    }


def test_analyze_import_compares_note_fields_independently_from_tags(db):
    db.add(Note(id="note-1", title="Imported", content="body", summary=None,
                created_at=NOW, updated_at=NOW, synced=False))
    db.add(Tag(id="tag-db", name="database-only", created_at=NOW))
    db.commit()

    report = analyze_import(db, _document(notes=[_note("note-1")]))

    assert report["clean"] is True
    assert report["entities"]["notes"] == [
        {"id": "note-1", "status": "identical", "differences": []}
    ]
    assert report["database_only"]["tags"] == ["tag-db"]


def test_soft_import_creates_new_entities_and_rejects_conflicting_ones(db):
    db.add(Note(id="conflict", title="Database", content="body", summary=None,
                created_at=NOW, updated_at=NOW, synced=False))
    db.commit()
    document = _document(notes=[_note("new"), _note("conflict", title="Imported")])

    report = apply_import(db, document, mode="soft")

    assert db.get(Note, "new").title == "Imported"
    assert db.get(Note, "conflict").title == "Database"
    statuses = {row["id"]: row["resolution"] for row in report["entities"]["notes"]}
    assert statuses == {"conflict": "rejected", "new": "created"}


def test_force_import_overwrites_without_deleting_database_only_rows(db):
    db.add_all([
        Note(id="conflict", title="Database", content="body", summary=None,
             created_at=NOW, updated_at=NOW, synced=False),
        Note(id="db-only", title="Keep", content="untouched", summary=None,
             created_at=NOW, updated_at=NOW, synced=False),
    ])
    db.commit()

    report = apply_import(
        db, _document(notes=[_note("conflict", title="Imported")]), mode="force"
    )

    assert db.get(Note, "conflict").title == "Imported"
    assert db.get(Note, "db-only").title == "Keep"
    assert report["entities"]["notes"][0]["resolution"] == "overwritten"
    assert report["database_only"]["notes"] == ["db-only"]
    assert report["sync_note_ids"] == ["conflict"]


def test_import_creates_dependencies_before_associations_and_links(db):
    tag = {"id": "tag-1", "name": "topic", "created_at": NOW.isoformat()}
    relation = {
        "id": "relation-1", "name": "references", "description": None,
        "is_bidirectional": False, "created_at": NOW.isoformat(),
    }
    link = {
        "id": "link-1", "source_id": "source", "target_id": "target",
        "relation_type_id": "relation-1", "description": None,
        "created_at": NOW.isoformat(),
    }
    association = {
        "note_id": "source", "tag_id": "tag-1", "created_at": NOW.isoformat(),
    }
    document = _document(
        notes=[_note("source"), _note("target")], tags=[tag],
        note_tags=[association], relation_types=[relation], links=[link],
    )

    apply_import(db, document, mode="soft")

    assert db.get(NoteTag, ("source", "tag-1")) is not None
    assert db.get(Link, "link-1").relation_type_id == "relation-1"


def test_dry_run_reports_missing_link_dependency_as_invalid(db):
    link = {
        "id": "broken", "source_id": "missing", "target_id": "also-missing",
        "relation_type_id": "no-relation", "description": None,
        "created_at": NOW.isoformat(),
    }

    report = analyze_import(db, _document(links=[link]))

    entry = report["entities"]["links"][0]
    assert entry["status"] == "invalid"
    assert set(entry["differences"]) == {"source_id", "target_id", "relation_type_id"}
    assert report["clean"] is False


def test_soft_import_rejects_invalid_entity_without_rolling_back_clean_rows(db):
    broken = {
        "note_id": "new", "tag_id": "missing-tag", "created_at": NOW.isoformat(),
    }
    report = apply_import(
        db, _document(notes=[_note("new")], note_tags=[broken]), mode="soft"
    )

    assert db.get(Note, "new") is not None
    assert db.get(NoteTag, ("new", "missing-tag")) is None
    assert report["entities"]["note_tags"][0]["resolution"] == "rejected"


def test_import_document_rejects_duplicate_tag_names(db):
    tags = [
        {"id": "tag-1", "name": "Topic", "created_at": NOW.isoformat()},
        {"id": "tag-2", "name": "topic", "created_at": NOW.isoformat()},
    ]

    with pytest.raises(ValidationError, match="duplicate names in tags"):
        analyze_import(db, _document(tags=tags))


def test_unique_tag_name_collision_is_reported_invalid(db):
    db.add(Tag(id="database-tag", name="Topic", created_at=NOW))
    db.commit()
    imported = {"id": "imported-tag", "name": "topic", "created_at": NOW.isoformat()}

    report = analyze_import(db, _document(tags=[imported]))

    assert report["entities"]["tags"][0] == {
        "id": "imported-tag", "status": "invalid", "differences": ["name"]
    }


def test_force_rejects_existing_link_update_with_missing_dependency(db):
    db.add_all([
        Note(id="source", title="Source", content="body", created_at=NOW,
             updated_at=NOW, synced=False),
        Note(id="target", title="Target", content="body", created_at=NOW,
             updated_at=NOW, synced=False),
        RelationType(id="relation", name="references", created_at=NOW),
    ])
    db.commit()
    db.add(Link(id="link", source_id="source", target_id="target",
                relation_type_id="relation", created_at=NOW))
    db.commit()
    changed = {
        "id": "link", "source_id": "missing", "target_id": "target",
        "relation_type_id": "relation", "description": None,
        "created_at": NOW.isoformat(),
    }

    report = apply_import(db, _document(links=[changed]), mode="force")

    assert report["entities"]["links"][0]["status"] == "invalid"
    assert report["entities"]["links"][0]["resolution"] == "rejected"
    assert db.get(Link, "link").source_id == "source"


def test_soft_link_uses_preserved_database_relation_when_import_conflicts(db):
    db.add_all([
        Note(id="source", title="Source", content="body", created_at=NOW,
             updated_at=NOW, synced=False),
        Note(id="target", title="Target", content="body", created_at=NOW,
             updated_at=NOW, synced=False),
        RelationType(id="relation", name="database-name", created_at=NOW),
    ])
    db.commit()
    relation = {
        "id": "relation", "name": "imported-name", "description": None,
        "is_bidirectional": False, "created_at": NOW.isoformat(),
    }
    link = {
        "id": "link", "source_id": "source", "target_id": "target",
        "relation_type_id": "relation", "description": None,
        "created_at": NOW.isoformat(),
    }

    report = apply_import(
        db, _document(relation_types=[relation], links=[link]), mode="soft"
    )

    assert report["entities"]["relation_types"][0]["resolution"] == "rejected"
    assert report["entities"]["links"][0]["resolution"] == "created"
    assert db.get(Link, "link").relation_type_id == "relation"


def test_force_tag_rename_resynchronizes_associated_notes(db):
    db.add_all([
        Note(id="note", title="Note", content="body", created_at=NOW,
             updated_at=NOW, synced=True),
        Tag(id="tag", name="old", created_at=NOW),
        NoteTag(note_id="note", tag_id="tag", created_at=NOW),
    ])
    db.commit()
    imported = {"id": "tag", "name": "new", "created_at": NOW.isoformat()}

    report = apply_import(db, _document(tags=[imported]), mode="force")

    assert report["sync_note_ids"] == ["note"]


def test_focused_report_still_lists_database_only_ids(db):
    db.add(Note(id="db-only", title="Keep", content="body", created_at=NOW,
                updated_at=NOW, synced=False))
    db.commit()

    report = analyze_import(
        db, _document(notes=[_note("selected")]),
        selection={"type": "notes", "id": "selected"},
    )

    assert report["database_only"]["notes"] == ["db-only"]


def test_selected_link_creates_new_imported_relation_dependency(db):
    db.add_all([
        Note(id="source", title="Source", content="body", created_at=NOW,
             updated_at=NOW, synced=False),
        Note(id="target", title="Target", content="body", created_at=NOW,
             updated_at=NOW, synced=False),
    ])
    db.commit()
    relation = {
        "id": "relation-1", "name": "references", "description": None,
        "is_bidirectional": False, "created_at": NOW.isoformat(),
    }
    link = {
        "id": "link-1", "source_id": "source", "target_id": "target",
        "relation_type_id": "relation-1", "description": None,
        "created_at": NOW.isoformat(),
    }

    report = apply_import(
        db, _document(relation_types=[relation], links=[link]), mode="soft",
        selection={"type": "links", "id": "link-1"},
    )

    assert db.get(RelationType, "relation-1") is not None
    assert db.get(Link, "link-1") is not None
    assert report["entities"]["relation_types"][0]["dependency"] is True
