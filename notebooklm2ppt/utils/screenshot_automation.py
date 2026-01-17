"""Automate Microsoft PC Manager's Smart Selection feature.

Steps:
1) Send Ctrl+Shift+A to open the Smart Selection tool
2) Drag from top-left to bottom-right to select full screen
3) Click the Done button to save the screenshot as PPT

When running this script, make sure the screen you want to capture is visible.

Note: Uses Microsoft PC Manager's Smart Selection feature by default (shortcut: Ctrl+Shift+A)
"""

import re
import time
import threading
import cv2
import win32api
import win32gui
import win32con
from pywinauto import mouse, keyboard

# Get screen dimensions
screen_width = win32api.GetSystemMetrics(0)
screen_height = win32api.GetSystemMetrics(1)


def get_ppt_windows():
    """Get the list of all current PowerPoint window handles"""
    ppt_windows = []
    
    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            # PowerPoint window class name is usually "PPTFrameClass"
            if "PPTFrameClass" in class_name or "PowerPoint" in window_text:
                results.append(hwnd)
        return True
    
    win32gui.EnumWindows(enum_callback, ppt_windows)
    return ppt_windows


def get_explorer_windows():
    """Get the list of all current File Explorer window handles"""
    explorer_windows = []
    
    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            # File Explorer window class name is usually "CabinetWClass"
            if "CabinetWClass" in class_name:
                results.append((hwnd, window_text))
        return True
    
    win32gui.EnumWindows(enum_callback, explorer_windows)
    return explorer_windows


def check_new_ppt_window(initial_windows, timeout=30, check_interval=1):
    """
    Check if a new PPT window has appeared
    
    Args:
        initial_windows: Initial list of PPT window handles
        timeout: Timeout in seconds, default 30
        check_interval: Check interval in seconds, default 1
    
    Returns:
        (bool, list, str): (whether new window found, list of new window handles, PPT filename)
    """
    print(f"\nStarting to monitor for new PowerPoint windows (timeout: {timeout} seconds)...")
    start_time = time.time()
    detected_new_window = False
    last_loading_window = None  # Last window that was "Opening"
    seen_windows = set(initial_windows)  # Track all seen windows
    
    while time.time() - start_time < timeout:
        current_windows = get_ppt_windows()
        new_windows = [w for w in current_windows if w not in seen_windows]
        
        # Update the list of seen windows
        seen_windows.update(new_windows)
        
        if new_windows or detected_new_window:
            if new_windows and not detected_new_window:
                elapsed = time.time() - start_time
                print(f"✓ Detected {len(new_windows)} new PowerPoint window(s) (elapsed: {elapsed:.1f}s)")
                detected_new_window = True
            
            # Check all current windows (not just new ones), as window titles may update
            all_new_windows = [w for w in current_windows if w not in initial_windows]
            
            for hwnd in all_new_windows:
                try:
                    window_text = win32gui.GetWindowText(hwnd)
                except:
                    continue
                
                # Check if it's in a temporary loading state
                is_loading = window_text and ("Opening" in window_text)
                
                if is_loading:
                    if hwnd != last_loading_window:
                        last_loading_window = hwnd
                        print(f"  - Window is loading: {window_text}, waiting for full load...")
                    continue
                
                # Found a valid filename (non-empty and not in loading state)
                # Exclude windows that only show "PowerPoint" without a filename
                if window_text and window_text.strip():
                    # If the window title is just "PowerPoint", the filename hasn't loaded yet, continue waiting
                    if window_text.strip().lower() == "powerpoint":
                        if hwnd != last_loading_window:
                            last_loading_window = hwnd
                            print(f"  - Window title not fully loaded (only shows 'PowerPoint'), continuing to wait...")
                        continue
                    
                    print(f"  ✓ Window loaded: {window_text}")
                    
                    # If it's a SmartCopy window, close it automatically after identification
                    if "smartcopy" in window_text.lower():
                        try:
                            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                            print(f"  → SmartCopy window identified and closed")
                        except Exception as e:
                            print(f"  → Failed to close SmartCopy window: {e}")
                    
                    return True, all_new_windows, window_text
        
        remaining = timeout - (time.time() - start_time)
        if remaining > 0:
            if detected_new_window:
                print(f"  Waiting for window title to update... (remaining: {remaining:.0f}s)", end='\r')
            else:
                print(f"  Waiting... (remaining: {remaining:.0f}s)", end='\r')
            time.sleep(check_interval)
    
    # Timeout, but if we detected an "Opening" window, return success but filename as None
    # so the caller can try to find the most recent file
    if detected_new_window:
        print(f"\n⚠ Window title did not update, will try to find the most recent PPT file")
        all_new_windows = [w for w in get_ppt_windows() if w not in initial_windows]
        return True, all_new_windows, None
    
    print(f"\n✗ No new PowerPoint window detected within {timeout} seconds")
    return False, [], None


def check_and_close_download_folder(initial_explorer_windows, timeout=10, check_interval=0.5):
    """
    Check if new File Explorer windows have appeared (especially Downloads folder), close them if so
    
    Args:
        initial_explorer_windows: Initial list of File Explorer windows [(hwnd, title), ...]
        timeout: Timeout in seconds, default 10
        check_interval: Check interval in seconds, default 0.5
    
    Returns:
        int: Number of windows closed
    """
    print(f"\nStarting to monitor for new File Explorer windows (timeout: {timeout} seconds)...")
    start_time = time.time()
    closed_count = 0
    initial_hwnds = [hwnd for hwnd, _ in initial_explorer_windows]
    
    while time.time() - start_time < timeout:
        current_windows = get_explorer_windows()
        new_windows = [(hwnd, title) for hwnd, title in current_windows if hwnd not in initial_hwnds]
        
        if new_windows:
            for hwnd, title in new_windows:
                try:
                    # Check if it's the Downloads folder (title usually contains "Downloads")
                    is_download_folder = "Downloads" in title
                    
                    print(f"✓ Detected new File Explorer window: {title}")
                    if is_download_folder:
                        print(f"  → Detected Downloads folder, closing...")
                    
                    # Close new windows (close any newly opened explorer window, not just Downloads)
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    closed_count += 1
                    print(f"  → Close command sent")
                    
                    # Add processed window to initial list to avoid re-processing
                    initial_hwnds.append(hwnd)
                    
                except Exception as e:
                    print(f"  → Failed to close window: {e}")
        
        remaining = timeout - (time.time() - start_time)
        if remaining > 0:
            time.sleep(check_interval)
    
    if closed_count > 0:
        print(f"\n✓ Closed {closed_count} File Explorer window(s)")
    else:
        print(f"\n✓ No new File Explorer windows detected")
    
    return closed_count


OFFSET_319 = 175
OFFSET_LEGACY = 210

def _compute_done_button_offset(pc_manager_version: str | None, fallback: int) -> int:
    """Infer the done-button offset based on PC Manager version."""
    if not pc_manager_version:
        return fallback

    normalized = pc_manager_version.strip().lower()
    numeric_match = re.match(r"(\d+(?:\.\d+)?)", normalized)
    if numeric_match:
        try:
            numeric_version = float(numeric_match.group(1))
            return OFFSET_319 if numeric_version >= 3.19 else OFFSET_LEGACY
        except ValueError:
            pass

    if "3.19" in normalized or "+" in normalized or "after" in normalized or "new" in normalized:
        return OFFSET_319
    return fallback


def take_fullscreen_snip(
    delay_before_hotkey: float = 1.0,
    drag_duration: float = 3,
    click_duration: float = 0.1,
    check_ppt_window: bool = True,
    ppt_check_timeout: float = 30,
    width: int = screen_width,
    height: int = screen_height,
    done_button_right_offset: int | None = None,
    pc_manager_version: str | None = None,
) -> tuple:
    """Take a full-screen screenshot using Microsoft PC Manager's Smart Selection feature.

    Args:
        delay_before_hotkey: Seconds to wait before sending Ctrl+Shift+A
        drag_duration: Seconds for the drag operation (simulated wait)
        click_duration: Seconds for clicking the Done button
        check_ppt_window: Whether to check for new PPT windows, default True
        ppt_check_timeout: PPT window detection timeout in seconds, default 30
        width: Screenshot width, defaults to screen width
        height: Screenshot height, defaults to screen height
        done_button_right_offset: Right offset in pixels for the Done button, for manual override
        pc_manager_version: PC Manager version; 3.19 and above uses 190, below 3.19 uses 210
    
    Returns:
        tuple: (bool, str) - (whether new window detected successfully, PPT filename)
               If PPT window checking is not needed, returns (True, None)
    """
    
    # Record PPT windows and File Explorer windows before clicking
    initial_ppt_windows = get_ppt_windows() if check_ppt_window else []
    initial_explorer_windows = get_explorer_windows()
    
    if check_ppt_window:
        print(f"PPT windows before click: {len(initial_ppt_windows)}")
    print(f"File Explorer windows before click: {len(initial_explorer_windows)}")

    # Wait for user to focus on the correct window
    time.sleep(delay_before_hotkey)

    # Open Microsoft PC Manager's Smart Selection tool
    # pywinauto uses '^+a' to represent Ctrl+Shift+A
    keyboard.send_keys('^+a')
    time.sleep(2)

    # Define key points for the snip and confirmation click.
    # top_left = (5, 5)
    top_left = (0,0)
    # delta = 4  # Small offset to ensure full coverage
    delta = int(width / 512 * 4)
    bottom_right = (width+delta, height)

    center = (width // 2, height // 2)

    if done_button_right_offset is not None:
        resolved_offset = done_button_right_offset
        offset_source = "manually specified"
    else:
        resolved_offset = _compute_done_button_offset(
            pc_manager_version,
            fallback=OFFSET_LEGACY,
        )
        offset_source = "version inferred/default"
    print(f"Done button offset: {resolved_offset} ({offset_source})")
    done_button = (bottom_right[0] - resolved_offset, height + 35)

    if done_button[1] > screen_height:
        done_button = (done_button[0], height - 35)

    print(bottom_right, width)

    # Perform the drag operation
    # Move to start position
    mouse.move(coords=top_left)
    
    # Press left button
    mouse.press(button='left', coords=top_left)
    
    # Wait for the duration to simulate the drag time

    time.sleep(1)
    


    # Release left button
    mouse.release(button='left', coords=bottom_right)

    # Optional: Click done button (commented out in original)
    mouse.move(coords=done_button)
    time.sleep(1)
    
    mouse.click(button='left', coords=done_button)
    
    # Check if a new PPT window appeared
    if check_ppt_window:
        success, new_windows, ppt_filename = check_new_ppt_window(initial_ppt_windows, timeout=ppt_check_timeout)
        
        # Also check for and close newly opened File Explorer windows (Downloads folder)
        check_and_close_download_folder(initial_explorer_windows, timeout=10)
        
        return success, ppt_filename
    
    return True, None

if __name__ == "__main__":
    from .image_viewer import show_image_fullscreen

    image_path = "Hackathon_Architect_Playbook_pngs/page_0001.png"

    stop_event = threading.Event()

    def _viewer():
        # Open fullscreen window
        show_image_fullscreen(image_path)
        # Maintain OpenCV event loop, otherwise window may not refresh
        while not stop_event.is_set():
            # Process GUI events; keep window responsive
            cv2.waitKey(50)
        # Close window when stopping
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    t = threading.Thread(target=_viewer, name="opencv_viewer", daemon=True)
    t.start()

    # Wait for window to stabilize before starting screenshot
    time.sleep(2)
    try:
        take_fullscreen_snip()
    finally:
        # Notify window to close and wait for thread to exit
        stop_event.set()
        t.join(timeout=2)
