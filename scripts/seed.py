#!/usr/bin/env python3
"""
Seed the memory API with the smart-home test dataset.

Usage:
    python scripts/seed.py
    python scripts/seed.py --api-url http://localhost:8001
    python scripts/seed.py --wipe          # delete all notes first
    python scripts/seed.py --buffer        # also seed 5 buffer notes
    python scripts/seed.py --wipe --buffer

Environment:
    MEMORY_API_URL  — overrides --api-url (default: http://localhost:8000)
    MEMORY_API_KEY  — optional API key (X-API-Key header)
"""

import argparse
import os
import sys

import httpx

# Allow importing from tests/integration/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tests"))
from integration.fixtures import NOTES, LINKS, BUFFER_NOTES  # noqa: E402


def wipe_all(client: httpx.Client) -> None:
    print("==> Wiping existing data...")

    # Delete all notes (cascades to links, note_tags, Qdrant vectors)
    resp = client.get("/api/notes/", params={"limit": 200})
    resp.raise_for_status()
    notes = resp.json().get("notes", [])
    for note in notes:
        client.delete(f"/api/notes/{note['id']}").raise_for_status()
    print(f"    Deleted {len(notes)} notes")

    # Delete all buffer notes
    resp = client.get("/api/buffer/", params={"limit": 200})
    resp.raise_for_status()
    buffer = resp.json().get("buffer_notes", [])
    for bn in buffer:
        client.delete(f"/api/buffer/{bn['id']}").raise_for_status()
    print(f"    Deleted {len(buffer)} buffer notes")

    # Delete all tags (orphaned after notes removed)
    resp = client.get("/api/tags/", params={"limit": 200})
    resp.raise_for_status()
    tags = resp.json().get("tags", [])
    for tag in tags:
        client.delete(f"/api/tags/{tag['id']}").raise_for_status()
    print(f"    Deleted {len(tags)} tags")


def seed_notes(client: httpx.Client) -> dict[str, str]:
    print(f"==> Seeding {len(NOTES)} notes...")
    note_ids: dict[str, str] = {}
    for note in NOTES:
        resp = client.post("/api/notes/", json=note)
        if resp.status_code != 201:
            print(f"    ERROR creating '{note['title']}': {resp.status_code} {resp.text}", file=sys.stderr)
            sys.exit(1)
        nid = resp.json()["id"]
        note_ids[note["title"]] = nid
        print(f"    [{nid[:8]}] {note['title']}")
    return note_ids


def seed_links(client: httpx.Client, note_ids: dict[str, str]) -> None:
    print(f"==> Seeding {len(LINKS)} links...")
    for source_title, target_title, relation_type in LINKS:
        resp = client.post("/api/notes/links", json={
            "source_id": note_ids[source_title],
            "target_id": note_ids[target_title],
            "relation_type": relation_type,
        })
        if resp.status_code != 201:
            print(f"    ERROR creating link {source_title!r} → {target_title!r}: {resp.status_code} {resp.text}", file=sys.stderr)
            sys.exit(1)
        print(f"    {source_title!r} --{relation_type}--> {target_title!r}")


def seed_buffer(client: httpx.Client) -> None:
    print(f"==> Seeding {len(BUFFER_NOTES)} buffer notes...")
    for bn in BUFFER_NOTES:
        resp = client.post("/api/buffer/", json=bn)
        if resp.status_code != 201:
            print(f"    ERROR creating buffer note: {resp.status_code} {resp.text}", file=sys.stderr)
            sys.exit(1)
        print(f"    [{resp.json()['id'][:8]}] {bn['content'][:60]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the memory API with test data")
    parser.add_argument(
        "--api-url",
        default=os.getenv("MEMORY_API_URL", "http://localhost:8000"),
        help="Base URL of the memory API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="Delete all existing notes, buffer notes, and tags before seeding",
    )
    parser.add_argument(
        "--buffer",
        action="store_true",
        help="Also seed buffer notes",
    )
    args = parser.parse_args()

    headers = {}
    api_key = os.getenv("MEMORY_API_KEY", "")
    if api_key:
        headers["X-API-Key"] = api_key

    client = httpx.Client(base_url=args.api_url, headers=headers, timeout=30)

    # Health check
    try:
        resp = client.get("/api/health")
        resp.raise_for_status()
    except Exception as e:
        print(f"ERROR: API not reachable at {args.api_url} — {e}", file=sys.stderr)
        sys.exit(1)

    print(f"==> Connected to {args.api_url}")

    if args.wipe:
        wipe_all(client)

    note_ids = seed_notes(client)
    seed_links(client, note_ids)

    if args.buffer:
        seed_buffer(client)

    print()
    print(f"==> Done. Seeded {len(NOTES)} notes, {len(LINKS)} links" +
          (f", {len(BUFFER_NOTES)} buffer notes" if args.buffer else "") + ".")
    print()
    print("Note IDs (for CLI testing):")
    for title, nid in note_ids.items():
        print(f"  {nid}  {title}")


if __name__ == "__main__":
    main()
