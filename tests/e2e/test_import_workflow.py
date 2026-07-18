import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("E2E_IMPORT_TESTS"), reason="Set E2E_IMPORT_TESTS=1"
)
API_URL = os.getenv("IMPORT_API_URL", "http://127.0.0.1:8004")
CLI_BIN = Path(os.getenv("CLI_BIN", "cli/dist/memory")).resolve()


def cli(*args: str, output: Path | None = None):
    env = os.environ | {"MEMORY_API_URL": API_URL}
    result = subprocess.run(
        [str(CLI_BIN), *args], env=env, text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
    if output is not None:
        output.write_text(result.stdout)
    return json.loads(result.stdout) if result.stdout.strip() else None


def wait_for_api():
    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            if httpx.get(f"{API_URL}/api/health", timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    pytest.fail("isolated import API did not become ready")


def entity(report, kind, entity_id):
    return next(row for row in report["entities"][kind] if row["id"] == entity_id)


def edit_vault(vault: Path, note_id: str, title: str):
    source = vault / f"{note_id}.md"
    text = source.read_text()
    source.write_text(
        re.sub(r"^title: .*$", f'title: "{title}"', text, count=1, flags=re.M)
    )
    new_id = str(uuid.uuid4())
    new_text = text.replace(note_id, new_id)
    new_text = re.sub(
        r"^title: .*$", f'title: "{title} new"', new_text, count=1, flags=re.M
    )
    new_text = re.sub(r"^route: .*$", f'route: "/{new_id}"', new_text, flags=re.M)
    (vault / f"{new_id}.md").write_text(new_text)
    return new_id


def test_import_end_to_end_all_sources_and_modes(tmp_path):
    wait_for_api()

    notes = []
    for index in range(6):
        notes.append(
            cli(
                "notes",
                "create",
                "--title",
                f"Import fixture {index}",
                "--content",
                f"Canonical fixture body {index}",
                "--tags",
                f"shared,topic-{index % 2}",
            )
        )
    cli("relations", "create", "--name", "references", "--description", "fixture")
    link = cli(
        "notes",
        "links",
        "link",
        "--source",
        notes[0]["id"],
        "--target",
        notes[1]["id"],
        "--relation-type",
        "references",
        "--description",
        "fixture link",
    )
    cli("buffer", "add", "--content", "fixture buffer", "--source", "e2e")

    canonical = tmp_path / "canonical.json"
    cli("export", "all", output=canonical)
    original = json.loads(canonical.read_text())
    assert len(original["notes"]) == 6
    assert len(original["links"]) == 1
    assert len(original["buffer_notes"]) == 1

    vaults = {}
    for format_name in ("obsidian", "wikijs"):
        vault = tmp_path / format_name
        cli("dump", "--output", str(vault), "--format", format_name)
        assert (vault / "zk-memory-manifest.json").is_file()
        assert len(list(vault.glob("*.md"))) == 6
        vaults[format_name] = vault

    # Diverge the database without deleting anything from the exported snapshot.
    conflict_id = notes[0]["id"]
    cli("notes", "update", conflict_id, "--title", "database conflict")
    db_only = cli(
        "notes",
        "create",
        "--title",
        "database-only note",
        "--content",
        "must survive every import",
        "--tags",
        "database-only-tag",
    )

    # Canonical JSON: add a clean dependency graph and edit an existing note.
    edited = json.loads(canonical.read_text())
    next(note for note in edited["notes"] if note["id"] == conflict_id)[
        "title"
    ] = "JSON restored title"
    now = "2026-07-18T00:00:00Z"
    new_note, new_tag, new_relation, new_link = (str(uuid.uuid4()) for _ in range(4))
    edited["notes"].append(
        {
            "id": new_note,
            "title": "JSON import-only",
            "content": "new body",
            "summary": None,
            "tags": ["json-new"],
            "synced": False,
            "sync_status": "pending",
            "sync_attempts": 0,
            "sync_last_error": None,
            "sync_last_attempt_at": None,
            "sync_last_success_at": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    edited["tags"].append({"id": new_tag, "name": "json-new", "created_at": now})
    edited["note_tags"].append(
        {"note_id": new_note, "tag_id": new_tag, "created_at": now}
    )
    edited["relation_types"].append(
        {
            "id": new_relation,
            "name": "json-relation",
            "description": None,
            "is_bidirectional": False,
            "created_at": now,
        }
    )
    edited["links"].append(
        {
            "id": new_link,
            "source_id": new_note,
            "target_id": notes[1]["id"],
            "relation_type_id": new_relation,
            "description": "new link",
            "created_at": now,
        }
    )
    edited_path = tmp_path / "edited.json"
    edited_path.write_text(json.dumps(edited))

    dry = cli("import", str(edited_path))
    assert entity(dry, "notes", conflict_id)["status"] == "conflicting"
    assert entity(dry, "notes", new_note)["status"] == "new"
    assert db_only["id"] in dry["database_only"]["notes"]

    soft = cli("import", str(edited_path), "--soft")
    assert entity(soft, "notes", conflict_id)["resolution"] == "rejected"
    assert entity(soft, "notes", new_note)["resolution"] == "created"
    assert entity(soft, "links", new_link)["resolution"] == "created"
    assert cli("notes", "get", conflict_id)["title"] == "database conflict"

    force = cli("import", str(edited_path), "--force")
    assert entity(force, "notes", conflict_id)["resolution"] == "overwritten"
    assert cli("notes", "get", conflict_id)["title"] == "JSON restored title"
    assert cli("notes", "get", db_only["id"])["title"] == "database-only note"

    # Each full Markdown vault exercises dry-run, soft, and force independently.
    for format_name, vault in vaults.items():
        vault_conflict = notes[2 if format_name == "obsidian" else 3]["id"]
        expected_title = f"{format_name} edited"
        vault_new = edit_vault(vault, vault_conflict, expected_title)

        dry = cli("import", str(vault))
        assert entity(dry, "notes", vault_conflict)["status"] == "conflicting"
        assert entity(dry, "notes", vault_new)["status"] == "new"
        assert db_only["id"] in dry["database_only"]["notes"]

        soft = cli("import", str(vault), "--soft")
        assert entity(soft, "notes", vault_conflict)["resolution"] == "rejected"
        assert entity(soft, "notes", vault_new)["resolution"] == "created"

        force = cli("import", str(vault), "--force")
        assert entity(force, "notes", vault_conflict)["resolution"] == "overwritten"
        assert cli("notes", "get", vault_conflict)["title"] == expected_title
        assert cli("notes", "get", db_only["id"])["title"] == "database-only note"

    # A standalone Markdown note must resolve existing tag names to DB tag IDs.
    standalone_id = notes[4]["id"]
    standalone = vaults["obsidian"] / f"{standalone_id}.md"
    database_title = cli("notes", "get", standalone_id)["title"]
    standalone.write_text(
        re.sub(
            r"^title: .*$",
            'title: "standalone edited"',
            standalone.read_text(),
            count=1,
            flags=re.M,
        )
    )
    standalone_report = cli("import", str(standalone))
    assert entity(standalone_report, "notes", standalone_id)["status"] == "conflicting"
    database_tags = {tag["name"].lower(): tag["id"] for tag in cli("tags", "list")}
    reported_tag_ids = {row["id"] for row in standalone_report["entities"]["tags"]}
    assert database_tags["shared"] in reported_tag_ids
    assert all(
        row["differences"] != ["name"] for row in standalone_report["entities"]["tags"]
    )
    soft = cli(
        "import", str(standalone), "--soft", "--type", "notes", "--id", standalone_id
    )
    assert entity(soft, "notes", standalone_id)["resolution"] == "rejected"
    assert cli("notes", "get", standalone_id)["title"] == database_title
    force = cli(
        "import", str(standalone), "--force", "--type", "notes", "--id", standalone_id
    )
    assert entity(force, "notes", standalone_id)["resolution"] == "overwritten"
    assert cli("notes", "get", standalone_id)["title"] == "standalone edited"

    final = cli("export", "all")
    final_ids = {note["id"] for note in final["notes"]}
    assert db_only["id"] in final_ids
    assert new_note in final_ids
    assert link["id"] in {item["id"] for item in final["links"]}
