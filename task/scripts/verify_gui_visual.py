"""
Smart Notes Assistant - Desktop GUI Visual Verification & Screenshot Capture
Phase 8: Premium Native Windows Desktop Application

Automates visual verification of all application screens on Windows 11:
1. Spawns/connects to the local FastAPI backend daemon.
2. Synchronizes starter notes so real data is present.
3. Systematically navigates through every required screen:
   - Dashboard (Dark theme)
   - All Notes (Grid view)
   - All Notes (List view)
   - Study Category View
   - Money Category View (with ₹ Indian Rupee symbol)
   - Travel Category View
   - Shopping Category View
   - Search View (with ranked results & relevance scores)
   - Note Editor Dialog (with live AI classification & uncertainty badge)
   - Settings & Diagnostics View
   - Dashboard (Light theme)
4. Captures genuine Windows pixel renderings via GDI PrintWindow into results/screenshots/
5. Cleanly shuts down the application and backend.
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import customtkinter as ctk
from PIL import Image

from src.gui.api_client import NotesApiClient
from src.gui.app import SmartNotesApp
from src.gui.backend_manager import BackendLifecycleManager
from src.gui.theme import theme_mgr
from src.gui.views.note_editor import NoteEditorDialog


def capture_window_to_file(window: ctk.CTk | ctk.CTkToplevel, output_path: Path) -> bool:
    """
    Capture the genuine rendered pixels of a CustomTkinter window on Windows 11
    using Windows GDI PrintWindow API.
    """
    window.update_idletasks()
    window.update()
    time.sleep(0.3)

    hwnd = window.winfo_id()
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    # Get true window rect dimensions
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width = rect.right - rect.left
    height = rect.bottom - rect.top

    if width <= 0 or height <= 0:
        width = window.winfo_width()
        height = window.winfo_height()

    hdc = user32.GetDC(hwnd)
    memdc = gdi32.CreateCompatibleDC(hdc)
    hbitmap = gdi32.CreateCompatibleBitmap(hdc, width, height)
    gdi32.SelectObject(memdc, hbitmap)

    # PW_RENDERFULLCONTENT = 2
    res = user32.PrintWindow(hwnd, memdc, 2)
    if not res:
        # Fallback to standard PrintWindow
        user32.PrintWindow(hwnd, memdc, 0)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = width
    bmi.biHeight = -height  # top-down DIB
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0

    buf = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits(memdc, hbitmap, 0, height, buf, ctypes.byref(bmi), 0)

    img = Image.frombuffer("RGBA", (width, height), buf, "raw", "BGRA", 0, 1)

    # Clean up GDI objects
    gdi32.DeleteObject(hbitmap)
    gdi32.DeleteDC(memdc)
    user32.ReleaseDC(hwnd, hdc)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="PNG")
    return output_path.exists()


def run_visual_verification() -> bool:
    print("=" * 75)
    print("SMART NOTES ASSISTANT - PHASE 8 WINDOWS VISUAL VERIFICATION & SCREENSHOTS")
    print("=" * 75)

    screenshots_dir = PROJECT_ROOT / "results" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    # 1. Start / connect backend daemon
    print("\n[1/5] Ensuring backend daemon is active on 127.0.0.1:8000...")
    backend_mgr = BackendLifecycleManager(project_root=PROJECT_ROOT)
    if not backend_mgr.ensure_backend_running():
        print("[ERROR] Failed to start backend service.")
        return False
    print("  - Backend service ready.")

    # 2. Synchronize starter notes via API client
    api_client = NotesApiClient()
    print("\n[2/5] Ensuring starter notes are loaded for authentic UI demonstration...")
    try:
        load_res = api_client.load_starter_notes()
        print(f"  - Starter notes synchronization: {load_res.get('message', 'OK')}")
    except Exception as e:
        print(f"  - Starter notes already present: {e}")

    # 3. Launch Application Window
    print("\n[3/5] Initializing SmartNotesApp CustomTkinter window...")
    theme_mgr.set_appearance_mode("dark")
    app = SmartNotesApp(api_client=api_client, backend_manager=backend_mgr)
    app.update_idletasks()
    app.update()
    time.sleep(1.0)  # Wait for initial note fetch
    app.update()

    captured_screens = []

    try:
        # Screen 1: Dashboard (Dark)
        print("\n[4/5] Capturing Application Screens...")
        app.navigate_to("Dashboard")
        app.update()
        shot1 = screenshots_dir / "01_dashboard_dark.png"
        capture_window_to_file(app, shot1)
        print(f"  [✓] 01_dashboard_dark.png saved ({shot1.stat().st_size // 1024} KB)")
        captured_screens.append("01_dashboard_dark.png")

        # Screen 2: All Notes (Grid)
        app.navigate_to("All Notes")
        app.views["Notes"]._on_view_toggle("Grid")
        app.update()
        shot2 = screenshots_dir / "02_all_notes_grid.png"
        capture_window_to_file(app, shot2)
        print(f"  [✓] 02_all_notes_grid.png saved ({shot2.stat().st_size // 1024} KB)")
        captured_screens.append("02_all_notes_grid.png")

        # Screen 3: All Notes (List)
        app.views["Notes"]._on_view_toggle("List")
        app.update()
        shot3 = screenshots_dir / "03_all_notes_list.png"
        capture_window_to_file(app, shot3)
        print(f"  [✓] 03_all_notes_list.png saved ({shot3.stat().st_size // 1024} KB)")
        captured_screens.append("03_all_notes_list.png")

        # Screen 4: Study Category
        app.navigate_to("Study")
        app.update()
        shot4 = screenshots_dir / "04_study_category.png"
        capture_window_to_file(app, shot4)
        print(f"  [✓] 04_study_category.png saved ({shot4.stat().st_size // 1024} KB)")
        captured_screens.append("04_study_category.png")

        # Screen 5: Money Category (With ₹ rupee symbol)
        app.navigate_to("Money")
        app.update()
        shot5 = screenshots_dir / "05_money_category.png"
        capture_window_to_file(app, shot5)
        print(f"  [✓] 05_money_category.png saved ({shot5.stat().st_size // 1024} KB)")
        captured_screens.append("05_money_category.png")

        # Screen 6: Travel Category
        app.navigate_to("Travel")
        app.update()
        shot6 = screenshots_dir / "06_travel_category.png"
        capture_window_to_file(app, shot6)
        print(f"  [✓] 06_travel_category.png saved ({shot6.stat().st_size // 1024} KB)")
        captured_screens.append("06_travel_category.png")

        # Screen 7: Shopping Category
        app.navigate_to("Shopping")
        app.update()
        shot7 = screenshots_dir / "07_shopping_category.png"
        capture_window_to_file(app, shot7)
        print(f"  [✓] 07_shopping_category.png saved ({shot7.stat().st_size // 1024} KB)")
        captured_screens.append("07_shopping_category.png")

        # Screen 8: Search View (with query & ranked results)
        app.navigate_to("Search")
        app.views["Search"].query_entry.delete(0, "end")
        app.views["Search"].query_entry.insert(0, "Python test exam")
        app.views["Search"]._perform_search()
        time.sleep(0.5)
        app.update()
        shot8 = screenshots_dir / "08_search_results.png"
        capture_window_to_file(app, shot8)
        print(f"  [✓] 08_search_results.png saved ({shot8.stat().st_size // 1024} KB)")
        captured_screens.append("08_search_results.png")

        # Screen 9: Note Editor Dialog (Live Classification Preview)
        editor = NoteEditorDialog(
            parent=app,
            api_client=api_client,
            note=None,
        )
        editor.textbox.delete("1.0", "end")
        editor.textbox.insert("1.0", "Deposit ₹10,000 into high-interest fixed savings account.")
        editor._trigger_classification_preview()
        time.sleep(0.6)
        editor.update()
        shot9 = screenshots_dir / "09_note_editor_preview.png"
        capture_window_to_file(editor, shot9)
        print(f"  [✓] 09_note_editor_preview.png saved ({shot9.stat().st_size // 1024} KB)")
        captured_screens.append("09_note_editor_preview.png")
        editor.destroy()

        # Screen 10: Settings & Diagnostics View
        app.navigate_to("Settings")
        app.update()
        time.sleep(0.4)
        app.update()
        shot10 = screenshots_dir / "10_settings_diagnostics.png"
        capture_window_to_file(app, shot10)
        print(f"  [✓] 10_settings_diagnostics.png saved ({shot10.stat().st_size // 1024} KB)")
        captured_screens.append("10_settings_diagnostics.png")

        # Screen 11: Dashboard (Light Theme)
        theme_mgr.set_appearance_mode("light")
        app._on_theme_changed("light")
        app.navigate_to("Dashboard")
        app.update()
        time.sleep(0.4)
        app.update()
        shot11 = screenshots_dir / "11_dashboard_light.png"
        capture_window_to_file(app, shot11)
        print(f"  [✓] 11_dashboard_light.png saved ({shot11.stat().st_size // 1024} KB)")
        captured_screens.append("11_dashboard_light.png")

        # Revert theme to dark default
        theme_mgr.set_appearance_mode("dark")

    finally:
        print("\n[5/5] Closing application window and cleaning up...")
        app.destroy()
        backend_mgr.stop()
        api_client.close()

    print("\n" + "=" * 75)
    print(f"VISUAL VERIFICATION COMPLETE: {len(captured_screens)} SCREENSHOTS CAPTURED")
    print("=" * 75)
    return True


if __name__ == "__main__":
    ok = run_visual_verification()
    sys.exit(0 if ok else 1)

