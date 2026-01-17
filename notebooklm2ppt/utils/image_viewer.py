# -*- coding: utf-8 -*-
# D:/research/ICCV/vis_pixel_fake_rebuttal3/example_page.png

# Use OpenCV to open an image, scale it to screen ratio and display fullscreen; no borders/toolbars.

import os
import sys
import ctypes
import cv2
import numpy as np
from PIL import Image


def _get_screen_resolution():
    # Windows: get screen resolution and enable DPI awareness to avoid scaling issues
    try:
        user32 = ctypes.windll.user32
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return 1920, 1080


def show_image_fullscreen(image_path: str, display_height: int = None):
    """
    Display image at the top-left corner of the screen
    
    Args:
        image_path: Path to the image
        display_height: Specified display height (pixels), if None it will auto-fit to screen
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    img = Image.open(image_path).convert("RGB")
    # img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    img = np.array(img)[...,::-1]  # RGB to BGR
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")

    screen_w, screen_h = _get_screen_resolution()
    h, w = img.shape[:2]

    # Calculate scale ratio based on specified height or screen size
    if display_height is not None:
        scale = display_height / h
    else:
        scale = min(screen_w / w, screen_h / h)
    
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))

    interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
    resized = cv2.resize(img, (new_w, new_h), interpolation=interp)

    # Place at top-left corner (not centered)
    pad_left = 0
    pad_right = max(0, screen_w - new_w)
    pad_top = 0
    pad_bottom = max(0, screen_h - new_h)
    canvas = cv2.copyMakeBorder(
        resized, pad_top, pad_bottom, pad_left, pad_right,
        borderType=cv2.BORDER_CONSTANT, value=(0, 0, 0)
    )

    win_name = "__opencv_fullscreen__"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(win_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow(win_name, canvas)

    # Set window to topmost (Windows)
    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, win_name)
        if hwnd:
            # SetWindowPos(HWND_TOPMOST= -1)
            ctypes.windll.user32.SetWindowPos(
                hwnd,
                -1,
                0,
                0,
                0,
                0,
                0x0002 | 0x0001  # SWP_NOSIZE | SWP_NOMOVE
            )
            # Force activate window to prevent it from going to background
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.BringWindowToTop(hwnd)
    except Exception:
        pass

    # # Press any key or ESC to exit
    # key = cv2.waitKey(0)
    # if key == 27:  # ESC
    #     pass
    # cv2.destroyAllWindows()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "example_page.png"
    # If a second argument is provided, use it as the display height
    height = int(sys.argv[2]) if len(sys.argv) > 2 else None
    show_image_fullscreen(path, display_height=height)