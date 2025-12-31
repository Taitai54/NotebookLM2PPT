"""自动化微软电脑管家的智能圈选功能。

步骤:
1) 发送 Ctrl+Shift+A 打开智能圈选工具
2) 从左上角拖动到右下角选择全屏
3) 点击完成按钮以保存截图为 PPT

运行此脚本时，需要确保要捕获的屏幕可见。

注意：默认使用微软电脑管家的智能圈选功能（快捷键：Ctrl+Shift+A）
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
    """获取当前所有PowerPoint窗口的句柄列表"""
    ppt_windows = []
    
    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            # PowerPoint 窗口类名通常为 "PPTFrameClass"
            if "PPTFrameClass" in class_name or "PowerPoint" in window_text:
                results.append(hwnd)
        return True
    
    win32gui.EnumWindows(enum_callback, ppt_windows)
    return ppt_windows


def get_explorer_windows():
    """获取当前所有文件资源管理器窗口的句柄列表"""
    explorer_windows = []
    
    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            # 文件资源管理器窗口类名通常为 "CabinetWClass"
            if "CabinetWClass" in class_name:
                results.append((hwnd, window_text))
        return True
    
    win32gui.EnumWindows(enum_callback, explorer_windows)
    return explorer_windows


def check_new_ppt_window(initial_windows, timeout=30, check_interval=1):
    """
    检查是否出现新的PPT窗口
    
    参数:
        initial_windows: 初始的PPT窗口句柄列表
        timeout: 超时时间（秒），默认30秒
        check_interval: 检查间隔（秒），默认1秒
    
    返回:
        (bool, list, str): (是否找到新窗口, 新窗口句柄列表, PPT文件名)
    """
    print(f"\n开始监测新的PowerPoint窗口 (超时时间: {timeout}秒)...")
    start_time = time.time()
    detected_new_window = False
    last_loading_window = None  # 最后一个"正在打开"的窗口
    seen_windows = set(initial_windows)  # 追踪所有见过的窗口
    
    while time.time() - start_time < timeout:
        current_windows = get_ppt_windows()
        new_windows = [w for w in current_windows if w not in seen_windows]
        
        # 更新已见过的窗口列表
        seen_windows.update(new_windows)
        
        if new_windows or detected_new_window:
            if new_windows and not detected_new_window:
                elapsed = time.time() - start_time
                print(f"✓ 检测到 {len(new_windows)} 个新的PowerPoint窗口 (耗时: {elapsed:.1f}秒)")
                detected_new_window = True
            
            # 检查所有当前窗口（不只是新窗口），因为窗口标题可能会更新
            all_new_windows = [w for w in current_windows if w not in initial_windows]
            
            for hwnd in all_new_windows:
                try:
                    window_text = win32gui.GetWindowText(hwnd)
                except:
                    continue
                
                # 检查是否是临时加载状态
                is_loading = window_text and ("正在打开" in window_text or "Opening" in window_text)
                
                if is_loading:
                    if hwnd != last_loading_window:
                        last_loading_window = hwnd
                        print(f"  - 检测到窗口正在加载: {window_text}，等待完全加载...")
                    continue
                
                # 找到有效的文件名（非空且不是加载状态）
                # 排除只有"PowerPoint"而没有文件名的情况
                if window_text and window_text.strip():
                    # 如果窗口标题只是"PowerPoint"，说明文件名还没有加载，继续等待
                    if window_text.strip().lower() == "powerpoint":
                        if hwnd != last_loading_window:
                            last_loading_window = hwnd
                            print(f"  - 窗口标题尚未完全加载（仅显示'PowerPoint'），继续等待...")
                        continue
                    
                    print(f"  ✓ 窗口加载完成: {window_text}")
                    
                    # 如果是SmartCopy窗口，识别后自动关闭
                    if "smartcopy" in window_text.lower():
                        try:
                            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                            print(f"  → SmartCopy窗口已识别并关闭")
                        except Exception as e:
                            print(f"  → 关闭SmartCopy窗口失败: {e}")
                    
                    return True, all_new_windows, window_text
        
        remaining = timeout - (time.time() - start_time)
        if remaining > 0:
            if detected_new_window:
                print(f"  等待窗口标题更新... (剩余: {remaining:.0f}秒)", end='\r')
            else:
                print(f"  等待中... (剩余: {remaining:.0f}秒)", end='\r')
            time.sleep(check_interval)
    
    # 超时了，但如果检测到了"正在打开"的窗口，返回成功但文件名为None
    # 这样调用方可以尝试查找最近的文件
    if detected_new_window:
        print(f"\n⚠ 窗口标题未更新，将尝试查找最近的PPT文件")
        all_new_windows = [w for w in get_ppt_windows() if w not in initial_windows]
        return True, all_new_windows, None
    
    print(f"\n✗ 在 {timeout} 秒内未检测到新的PowerPoint窗口")
    return False, [], None


def check_and_close_download_folder(initial_explorer_windows, timeout=10, check_interval=0.5):
    """
    检查是否出现新的文件资源管理器窗口（特别是下载文件夹），如果有则关闭
    
    参数:
        initial_explorer_windows: 初始的文件资源管理器窗口列表 [(hwnd, title), ...]
        timeout: 超时时间（秒），默认10秒
        check_interval: 检查间隔（秒），默认0.5秒
    
    返回:
        int: 关闭的窗口数量
    """
    print(f"\n开始监测新的文件资源管理器窗口 (超时时间: {timeout}秒)...")
    start_time = time.time()
    closed_count = 0
    initial_hwnds = [hwnd for hwnd, _ in initial_explorer_windows]
    
    while time.time() - start_time < timeout:
        current_windows = get_explorer_windows()
        new_windows = [(hwnd, title) for hwnd, title in current_windows if hwnd not in initial_hwnds]
        
        if new_windows:
            for hwnd, title in new_windows:
                try:
                    # 检查是否是下载文件夹（标题通常包含"下载"或"Downloads"）
                    is_download_folder = "下载" in title or "Downloads" in title
                    
                    print(f"✓ 检测到新的文件资源管理器窗口: {title}")
                    if is_download_folder:
                        print(f"  → 检测到下载文件夹，正在关闭...")
                    
                    # 关闭新窗口（无论是否是下载文件夹，都关闭新打开的资源管理器）
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    closed_count += 1
                    print(f"  → 已发送关闭指令")
                    
                    # 将已处理的窗口加入初始列表，避免重复处理
                    initial_hwnds.append(hwnd)
                    
                except Exception as e:
                    print(f"  → 关闭窗口失败: {e}")
        
        remaining = timeout - (time.time() - start_time)
        if remaining > 0:
            time.sleep(check_interval)
    
    if closed_count > 0:
        print(f"\n✓ 共关闭 {closed_count} 个文件资源管理器窗口")
    else:
        print(f"\n✓ 未检测到新的文件资源管理器窗口")
    
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
    """使用微软电脑管家的智能圈选功能进行全屏截图。

    Args:
        delay_before_hotkey: 发送 Ctrl+Shift+A 之前等待的秒数
        drag_duration: 拖动操作持续的秒数（模拟等待）
        click_duration: 点击完成按钮的秒数
        check_ppt_window: 是否检查新的PPT窗口，默认True
        ppt_check_timeout: PPT窗口检测超时时间（秒），默认30
        width: 截图宽度，默认为屏幕宽度
        height: 截图高度，默认为屏幕高度
        done_button_right_offset: 完成按钮的右侧偏移量（像素），用于手动覆盖
        pc_manager_version: 电脑管家版本号；3.19及以上自动使用 190，低于3.19 使用 210
    
    Returns:
        tuple: (bool, str) - (是否成功检测到新窗口, PPT文件名)
               如果不需要检查PPT窗口，返回 (True, None)
    """
    
    # 记录点击前的PPT窗口和文件资源管理器窗口
    initial_ppt_windows = get_ppt_windows() if check_ppt_window else []
    initial_explorer_windows = get_explorer_windows()
    
    if check_ppt_window:
        print(f"点击前PPT窗口数量: {len(initial_ppt_windows)}")
    print(f"点击前文件资源管理器窗口数量: {len(initial_explorer_windows)}")

    # 等待用户聚焦到正确的窗口
    time.sleep(delay_before_hotkey)

    # 打开微软电脑管家的智能圈选工具
    # pywinauto 使用 '^+a' 表示 Ctrl+Shift+A
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
        offset_source = "手动指定"
    else:
        resolved_offset = _compute_done_button_offset(
            pc_manager_version,
            fallback=OFFSET_LEGACY,
        )
        offset_source = "版本推断/默认"
    print(f"完成按钮偏移: {resolved_offset} ({offset_source})")
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
    
    # 检查是否出现新的PPT窗口
    if check_ppt_window:
        success, new_windows, ppt_filename = check_new_ppt_window(initial_ppt_windows, timeout=ppt_check_timeout)
        
        # 同时检查并关闭新打开的文件资源管理器窗口（下载文件夹）
        check_and_close_download_folder(initial_explorer_windows, timeout=10)
        
        return success, ppt_filename
    
    return True, None

if __name__ == "__main__":
    from .image_viewer import show_image_fullscreen

    image_path = "Hackathon_Architect_Playbook_pngs/page_0001.png"

    stop_event = threading.Event()

    def _viewer():
        # 打开全屏窗口
        show_image_fullscreen(image_path)
        # 维持 OpenCV 事件循环，否则窗口可能不刷新
        while not stop_event.is_set():
            # 处理 GUI 事件；保持窗口响应
            cv2.waitKey(50)
        # 停止时关闭窗口
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    t = threading.Thread(target=_viewer, name="opencv_viewer", daemon=True)
    t.start()

    # 等待窗口稳定后开始截图
    time.sleep(2)
    try:
        take_fullscreen_snip()
    finally:
        # 通知关闭窗口并等待线程退出
        stop_event.set()
        t.join(timeout=2)
