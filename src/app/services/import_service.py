from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import BufferNote, Link, Note, NoteTag, RelationType, Tag
from app.models.import_schemas import ImportDocument, ImportMode, ImportSelection

_ENTITY_MODELS = {
    "notes": Note,
    "tags": Tag,
    "note_tags": NoteTag,
    "relation_types": RelationType,
    "links": Link,
    "buffer_notes": BufferNote,
}
_FIELDS = {
    "notes": (
        "title", "content", "summary", "synced", "sync_status", "sync_attempts",
        "sync_last_error", "sync_last_attempt_at", "sync_last_success_at",
        "created_at", "updated_at",
    ),
    "tags": ("name", "created_at"),
    "note_tags": ("note_id", "tag_id", "created_at"),
    "relation_types": ("name", "description", "is_bidirectional", "created_at"),
    "links": (
        "source_id", "target_id", "relation_type_id", "description", "created_at",
    ),
    "buffer_notes": (
        "content", "meta", "processed", "processed_at", "created_at", "updated_at",
    ),
}


def analyze_import(
    db: Session,
    document: ImportDocument | dict[str, Any],
    selection: ImportSelection | dict[str, str] | None = None,
    mode: ImportMode = "dry_run",
) -> dict[str, Any]:
    """Compare a canonical import document with SQL state without mutating it."""
    if not isinstance(document, ImportDocument):
        document = ImportDocument.model_validate(document)
    if selection is not None and not isinstance(selection, ImportSelection):
        selection = ImportSelection.model_validate(selection)

    entities: dict[str, list[dict[str, Any]]] = {name: [] for name in _ENTITY_MODELS}
    database_only: dict[str, list[str]] = {name: [] for name in _ENTITY_MODELS}
    imported_by_type = {
        name: {_row_id(name, row): row for row in getattr(document, name)}
        for name in _ENTITY_MODELS
    }
    database_by_type = {
        name: {
            _row_id(name, row): row for row in db.query(model).all()
        }
        for name, model in _ENTITY_MODELS.items()
    }
    selected_ids = _selected_entity_ids(
        document, selection, imported_by_type, database_by_type
    )

    for name in _ENTITY_MODELS:
        imported_rows = [
            imported_by_type[name][entity_id]
            for entity_id in sorted(selected_ids[name])
        ]
        database_by_id = database_by_type[name]

        for imported in imported_rows:
            entity_id = _row_id(name, imported)
            current = database_by_id.get(entity_id)
            differences: list[str] = []
            status = "new"
            if current is not None:
                differences = [
                    field
                    for field in _FIELDS[name]
                    if _comparable(getattr(imported, field))
                    != _comparable(getattr(current, field))
                ]
                status = "conflicting" if differences else "identical"
            invalid = _invalid_differences(
                db, name, imported, selected_ids, database_by_type, entities
            )
            if invalid:
                differences = list(dict.fromkeys(differences + invalid))
                status = "invalid"
            entry: dict[str, Any] = {
                "id": entity_id, "status": status, "differences": differences
            }
            if selection is not None and not (
                selection.entity_type == name and selection.entity_id == entity_id
            ):
                entry["dependency"] = True
            entities[name].append(entry)

        database_only[name] = sorted(
            set(database_by_id) - set(imported_by_type[name])
        )

    clean = not any(
        entry["status"] in {"conflicting", "invalid"}
        for entries in entities.values()
        for entry in entries
    )
    return {
        "mode": "dry_run",
        "clean": clean,
        "entities": entities,
        "database_only": database_only,
    }


def _selected_entity_ids(
    document: ImportDocument,
    selection: ImportSelection | None,
    imported: dict[str, dict[str, Any]],
    database: dict[str, dict[str, Any]],
) -> dict[str, set[str]]:
    if selection is None:
        return {name: set(rows) for name, rows in imported.items()}
    if selection.entity_id not in imported[selection.entity_type]:
        raise ValueError(
            f"selected {selection.entity_type} entity {selection.entity_id!r} is absent"
        )

    selected = {name: set() for name in _ENTITY_MODELS}
    selected[selection.entity_type].add(selection.entity_id)
    row = imported[selection.entity_type][selection.entity_id]
    dependencies: list[tuple[str, str]] = []
    if selection.entity_type == "note_tags":
        dependencies = [("notes", row.note_id), ("tags", row.tag_id)]
    elif selection.entity_type == "links":
        dependencies = [
            ("notes", row.source_id),
            ("notes", row.target_id),
            ("relation_types", row.relation_type_id),
        ]
    for entity_type, entity_id in dependencies:
        if entity_id not in database[entity_type] and entity_id in imported[entity_type]:
            selected[entity_type].add(entity_id)
    return selected


def _invalid_differences(
    db: Session,
    name: str,
    row: Any,
    selected: dict[str, set[str]],
    database: dict[str, dict[str, Any]],
    entities: dict[str, list[dict[str, Any]]],
) -> list[str]:
    differences: list[str] = []
    if name in {"tags", "relation_types"}:
        model = _ENTITY_MODELS[name]
        normalized_name = row.name.strip().lower()
        collision = (
            db.query(model)
            .filter(func.lower(func.trim(model.name)) == normalized_name)
            .first()
        )
        if collision is not None and collision.id != row.id:
            differences.append("name")
    references: list[tuple[str, str, str]] = []
    if name == "note_tags":
        references = [
            ("note_id", "notes", row.note_id), ("tag_id", "tags", row.tag_id)
        ]
    elif name == "links":
        references = [
            ("source_id", "notes", row.source_id),
            ("target_id", "notes", row.target_id),
            ("relation_type_id", "relation_types", row.relation_type_id),
        ]
    for field, entity_type, entity_id in references:
        dependency = next(
            (entry for entry in entities[entity_type] if entry["id"] == entity_id),
            None,
        )
        available = entity_id in database[entity_type]
        if dependency is not None and not available:
            available = dependency["status"] != "invalid"
        elif not available and entity_id in selected[entity_type]:
            available = False
        if not available:
            differences.append(field)
    return differences


def apply_import(
    db: Session,
    document: ImportDocument | dict[str, Any],
    mode: ImportMode,
    selection: ImportSelection | dict[str, str] | None = None,
) -> dict[str, Any]:
    """Apply a soft or force import in one SQL transaction."""
    if mode == "dry_run":
        return analyze_import(db, document, selection, mode)
    if not isinstance(document, ImportDocument):
        document = ImportDocument.model_validate(document)
    if selection is not None and not isinstance(selection, ImportSelection):
        selection = ImportSelection.model_validate(selection)

    report = analyze_import(db, document, selection, mode)
    sync_note_ids: set[str] = set()

    try:
        for name in _ENTITY_MODELS:
            imported = {_row_id(name, row): row for row in getattr(document, name)}
            for entry in report["entities"][name]:
                row = imported[entry["id"]]
                if entry["status"] == "identical":
                    entry["resolution"] = "unchanged"
                    continue
                if entry["status"] == "invalid" or (
                    entry["status"] == "conflicting" and mode == "soft"
                ):
                    entry["resolution"] = "rejected"
                    continue

                current = _get_row(db, name, row)
                values = {field: getattr(row, field) for field in _FIELDS[name]}
                if current is None:
                    values.update(_identity_values(name, row))
                    db.add(_ENTITY_MODELS[name](**values))
                    entry["resolution"] = "created"
                else:
                    for field, value in values.items():
                        setattr(current, field, value)
                    entry["resolution"] = "overwritten"
                if name == "notes" and (
                    current is None
                    or {"title", "content", "summary"}.intersection(entry["differences"])
                ):
                    sync_note_ids.add(row.id)
                elif name == "tags" and "name" in entry["differences"]:
                    sync_note_ids.update(
                        note_id
                        for (note_id,) in db.query(NoteTag.note_id)
                        .filter(NoteTag.tag_id == row.id)
                        .all()
                    )
                elif name == "note_tags":
                    sync_note_ids.add(row.note_id)
            db.flush()
        db.commit()
    except Exception:
        db.rollback()
        raise

    report["mode"] = mode
    report["applied"] = True
    report["sync_note_ids"] = sorted(sync_note_ids)
    return report


def _get_row(db: Session, name: str, row: Any):
    if name == "note_tags":
        return db.get(NoteTag, (row.note_id, row.tag_id))
    return db.get(_ENTITY_MODELS[name], row.id)


def _identity_values(name: str, row: Any) -> dict[str, str]:
    if name == "note_tags":
        return {"note_id": row.note_id, "tag_id": row.tag_id}
    return {"id": row.id}


def _row_id(name: str, row: Any) -> str:
    if name == "note_tags":
        return f"{row.note_id}:{row.tag_id}"
    return row.id


def _comparable(value: Any) -> Any:
    if isinstance(value, datetime):
        # SQLite returns naive values even when timezone-aware values were inserted.
        return value.replace(tzinfo=None).isoformat(timespec="microseconds")
    return value
