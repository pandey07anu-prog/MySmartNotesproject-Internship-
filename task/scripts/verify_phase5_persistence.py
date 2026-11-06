"""
Smart Notes Assistant - Phase 5 Persistence & Lifecycle Verification Script
Step 13: Separate Persistence Verification Runner

This script executes the exact 10-step persistence verification workflow:
1. Initialize the notes manager.
2. Load starter notes.
3. Add multiple notes.
4. Edit one note.
5. Delete one note.
6. Record the remaining IDs.
7. Reinitialize the manager.
8. Confirm that notes and metadata persist.
9. Add another note.
10. Confirm that the next ID is correct and no deleted ID is reused.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
from pathlib import Path

# Safe stdout encoding
if sys.stdout and getattr(sys.stdout, "encoding", None):
    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, io.UnsupportedOperation):
            pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.notes_manager import NotesManager


def run_persistence_verification() -> bool:
    print("=" * 75)
    print("SMART NOTES ASSISTANT - PHASE 5 PERSISTENCE VERIFICATION")
    print("=" * 75)

    with tempfile.TemporaryDirectory() as tmp_dir:
        test_storage_path = Path(tmp_dir) / "notes_verification.json"
        print(f"\nUsing isolated test storage: {test_storage_path}")

        # Step 1: Initialize Notes Manager
        print("\n[Step 1/10] Initializing NotesManager...")
        manager1 = NotesManager(storage_path=test_storage_path, uncertainty_threshold=0.40)
        print("  - Manager initialized successfully.")
        print(f"  - Initial note count: {manager1.count()}")
        print(f"  - Next note ID: {manager1.get_next_id()}")

        # Step 2: Load starter notes
        print("\n[Step 2/10] Loading starter notes from data/starter_notes.json...")
        starter_notes = manager1.load_starter_notes()
        print(f"  - Loaded {len(starter_notes)} starter notes (IDs: N001 to N012).")
        assert manager1.count() == 12, "Expected exactly 12 starter notes"
        assert manager1.get_next_id() == "N013", "Expected next ID to be N013"

        # Step 3: Add multiple notes
        print("\n[Step 3/10] Adding 3 new user notes...")
        note13 = manager1.add_note("Review backpropagation and gradient descent algorithms.")
        note14 = manager1.add_note("Transfer ₹7,500 to my emergency fund.")
        note15 = manager1.add_note("Book high-speed train tickets to Kyoto.")
        print(f"  - Added Note 1: ID={note13['id']}, Category={note13['category']}, Conf={note13['confidence']:.4f}, Uncertain={note13['uncertain']}")
        print(f"  - Added Note 2: ID={note14['id']}, Category={note14['category']}, Conf={note14['confidence']:.4f}, Uncertain={note14['uncertain']}")
        print(f"  - Added Note 3: ID={note15['id']}, Category={note15['category']}, Conf={note15['confidence']:.4f}, Uncertain={note15['uncertain']}")
        assert note13["id"] == "N013"
        assert note14["id"] == "N014"
        assert note15["id"] == "N015"
        assert manager1.count() == 15
        assert manager1.get_next_id() == "N016"

        # Step 4: Edit one note
        print("\n[Step 4/10] Editing note N013...")
        orig_created_at = note13["created_at"]
        updated13 = manager1.update_note(
            "N013",
            "Review Transformer attention mechanisms and BERT fine-tuning."
        )
        print(f"  - Updated N013: New Text=\"{updated13['text']}\"")
        print(f"  - Category: {updated13['category']}, Conf={updated13['confidence']:.4f}")
        print(f"  - Created At (preserved): {updated13['created_at']}")
        print(f"  - Updated At (refreshed): {updated13['updated_at']}")
        assert updated13["id"] == "N013"
        assert updated13["created_at"] == orig_created_at
        assert updated13["updated_at"] >= orig_created_at

        # Step 5: Delete one note
        print("\n[Step 5/10] Deleting note N014...")
        deleted14 = manager1.delete_note("N014")
        print(f"  - Deleted note: ID={deleted14['id']}, Text=\"{deleted14['text']}\"")
        assert manager1.count() == 14
        assert manager1.get_next_id() == "N016"

        # Step 6: Record remaining IDs
        print("\n[Step 6/10] Recording remaining IDs in session 1...")
        remaining_notes_s1 = manager1.get_all_notes()
        remaining_ids_s1 = [n["id"] for n in remaining_notes_s1]
        print(f"  - Remaining IDs ({len(remaining_ids_s1)} notes): {remaining_ids_s1}")
        assert "N014" not in remaining_ids_s1
        assert "N013" in remaining_ids_s1
        assert "N015" in remaining_ids_s1

        # Step 7: Reinitialize manager (simulating app restart)
        print("\n[Step 7/10] Reinitializing NotesManager from disk...")
        del manager1  # Destroy first instance
        manager2 = NotesManager(storage_path=test_storage_path, uncertainty_threshold=0.40)
        print("  - Fresh NotesManager instance created.")

        # Step 8: Confirm notes and metadata persist
        print("\n[Step 8/10] Verifying persistence of notes and metadata...")
        remaining_notes_s2 = manager2.get_all_notes()
        remaining_ids_s2 = [n["id"] for n in remaining_notes_s2]
        print(f"  - Session 2 note count: {manager2.count()}")
        print(f"  - Session 2 IDs: {remaining_ids_s2}")
        assert remaining_ids_s2 == remaining_ids_s1
        
        # Verify N013 has updated text and preserved created_at
        persisted_n13 = manager2.get_note("N013")
        assert persisted_n13["text"] == updated13["text"]
        assert persisted_n13["created_at"] == orig_created_at
        assert persisted_n13["updated_at"] == updated13["updated_at"]

        # Step 9: Add another note
        print("\n[Step 9/10] Adding note in session 2...")
        note16 = manager2.add_note("Buy groceries: olive oil, pasta, and fresh basil.")
        print(f"  - Added Note: ID={note16['id']}, Category={note16['category']}, Conf={note16['confidence']:.4f}")

        # Step 10: Confirm next ID is correct and no deleted ID is reused
        print("\n[Step 10/10] Verifying ID uniqueness and non-reuse of deleted IDs...")
        print(f"  - Newly assigned note ID: {note16['id']} (Expected: N016)")
        print(f"  - Deleted ID 'N014' was NOT reused.")
        print(f"  - New next_id counter: {manager2.get_next_id()} (Expected: N017)")
        assert note16["id"] == "N016"
        assert note16["id"] != "N014"
        assert manager2.get_next_id() == "N017"
        assert manager2.count() == 15

    print("\n" + "=" * 75)
    print("PHASE 5 PERSISTENCE VERIFICATION: ALL 10 STEPS PASSED SUCCESSFULLY")
    print("=" * 75 + "\n")
    return True


if __name__ == "__main__":
    success = run_persistence_verification()
    sys.exit(0 if success else 1)

