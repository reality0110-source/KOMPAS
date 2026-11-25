"""지도 창(Edge 앱 창)을 프로그램 화면 안에 끼워 넣는 윈도우 기능.

원리: 윈도우의 SetParent로 Edge 창을 프로그램 화면의 한 칸(tk Frame)의 '자식 창'으로 만들고,
제목표시줄 · 테두리를 없앤 뒤 칸 크기에 맞춰 늘리고 줄입니다.
"""
import ctypes
from ctypes import wintypes

_user32 = ctypes.WinDLL("user32", use_last_error=True)

GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_SYSMENU = 0x00080000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_EX_APPWINDOW = 0x00040000
WS_EX_WINDOWEDGE = 0x00000100
WS_EX_CLIENTEDGE = 0x00000200
WS_EX_DLGMODALFRAME = 0x00000001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
WM_CLOSE = 0x0010

_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
_user32.EnumWindows.argtypes = [_WNDENUMPROC, wintypes.LPARAM]
_user32.EnumChildWindows.argtypes = [wintypes.HWND, _WNDENUMPROC, wintypes.LPARAM]
_user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.IsWindow.argtypes = [wintypes.HWND]
_user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
_user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
_user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
_user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
_user32.SetParent.restype = wintypes.HWND
_user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, wintypes.UINT]
_user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]


def find_window(title, class_name="Chrome_WidgetWin_1"):
    """제목이 정확히 title인 최상위 창의 핸들(번호). 없으면 None."""
    found = []

    def _cb(hwnd, _):
        buf = ctypes.create_unicode_buffer(256)
        _user32.GetClassNameW(hwnd, buf, 256)
        if buf.value != class_name:
            return True
        _user32.GetWindowTextW(hwnd, buf, 256)
        if buf.value == title:
            found.append(hwnd)
            return False
        return True

    _user32.EnumWindows(_WNDENUMPROC(_cb), 0)
    return found[0] if found else None


def embed(hwnd, parent_hwnd, width, height):
    style = _user32.GetWindowLongPtrW(hwnd, GWL_STYLE)
    style &= ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
    _user32.SetWindowLongPtrW(hwnd, GWL_STYLE, style | WS_CHILD)
    ex = _user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    ex &= ~(WS_EX_APPWINDOW | WS_EX_WINDOWEDGE | WS_EX_CLIENTEDGE | WS_EX_DLGMODALFRAME)
    _user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex)
    _user32.SetParent(hwnd, parent_hwnd)
    _user32.SetWindowPos(hwnd, None, 0, 0, width, height,
                         SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED | SWP_SHOWWINDOW)


def _rect(hwnd):
    r = wintypes.RECT()
    _user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r


def frame_margins(hwnd, content_class="Chrome_RenderWidgetHostHWND"):
    """Edge가 스스로 그리는 제목표시줄 · 테두리 두께 (왼, 위, 오른, 아래). 웹 화면이 아직 없으면 None.

    Edge는 제목표시줄을 직접 그려서 스타일을 바꿔도 안 없어지므로, 웹 화면 영역이 창 안에서 어디 있는지 재서
    그만큼 창을 칸 밖으로 밀어냅니다."""
    found = []

    def _cb(child, _):
        buf = ctypes.create_unicode_buffer(64)
        _user32.GetClassNameW(child, buf, 64)
        if buf.value == content_class:
            found.append(child)
            return False
        return True

    _user32.EnumChildWindows(hwnd, _WNDENUMPROC(_cb), 0)
    if not found:
        return None
    w, c = _rect(hwnd), _rect(found[0])
    if c.right - c.left <= 0 or c.bottom - c.top <= 0:
        return None
    return (c.left - w.left, c.top - w.top, w.right - c.right, w.bottom - c.bottom)


def resize(hwnd, width, height, margins=None):
    left, top, right, bottom = margins or (0, 0, 0, 0)
    _user32.SetWindowPos(hwnd, None, -left, -top, width + left + right, height + top + bottom,
                         SWP_NOZORDER | SWP_NOACTIVATE)


def is_alive(hwnd):
    return bool(hwnd and _user32.IsWindow(hwnd))


def close(hwnd):
    if is_alive(hwnd):
        _user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
