"""지도 창 ↔ 프로그램 연결.

프로그램 안에 작은 웹서버(이 컴퓨터 안에서만 열림)를 띄우고 Edge/Chrome '앱 모드' 창으로 지도 페이지(web/map.html)를 엽니다.
지도는 OpenStreetMap이라 인증키가 필요 없습니다. 포트는 비어 있는 번호를 그때그때 씁니다.

  지도 클릭   → 지도 페이지가 POST /api/site 로 좌표 전송 → inbox(대기열)에 쌓임
  프로그램    → inbox를 주기적으로 꺼내 설치위치로 반영
  지도 페이지 → GET /api/state 로 현재 설치위치를 받아 표시를 맞춤

Edge는 실행 직후 첫 프로세스가 끝나고 다른 프로세스가 창을 넘겨받으므로 프로세스로는 창이 열려 있는지 알 수 없습니다.
대신 지도 페이지가 1초마다 보내는 /api/state 요청으로 판단하고, 프로그램을 닫을 때는 페이지가 스스로 창을 닫게 합니다.
"""
import functools
import json
import os
import queue
import subprocess
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PAGE = "map.html?embed=1"
WINDOW_TITLE = "KOMPAS 지도"      # web/map.html의 <title>과 같아야 함 (이 제목으로 창을 찾음)
ALIVE_SEC = 3.0
LAUNCH_GRACE_SEC = 10.0

_BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


class MapBridgeError(Exception):
    pass


class MapBridge:
    def __init__(self, web_dir, profile_dir, user_agent=None):
        self.web_dir = str(web_dir)
        self.profile_dir = str(profile_dir)
        self.user_agent = user_agent        # 지도 그림 서버(OpenStreetMap)에 이 프로그램을 밝히는 이름표 — 타일 이용 규정
        self.site = None
        self.inbox = queue.Queue()
        self._server = None
        self._last_poll = 0.0
        self._launched_at = 0.0
        self._closing = False
        self._close_sent = threading.Event()

    @property
    def port(self):
        return self._server.server_address[1] if self._server else None

    def _make_handler(self):
        bridge = self

        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def end_headers(self):
                self.send_header("Cache-Control", "no-store")     # 지도 페이지를 고치면 바로 반영되게
                super().end_headers()

            def _json(self, code, obj):
                body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path.startswith("/api/state"):
                    bridge._last_poll = time.time()
                    self._json(200, {"site": bridge.site, "close": bridge._closing})
                    if bridge._closing:
                        bridge._close_sent.set()
                else:
                    super().do_GET()

            def do_POST(self):
                if not self.path.startswith("/api/site"):
                    self._json(404, {"ok": False})
                    return
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    data = json.loads(self.rfile.read(length))
                    value = (float(data["lat"]), float(data["lon"]))
                except (ValueError, KeyError, TypeError):
                    self._json(400, {"ok": False})
                    return
                bridge.inbox.put(value)
                self._json(200, {"ok": True})

        return functools.partial(Handler, directory=self.web_dir)

    def _start_server(self):
        if self._server:
            return
        try:
            self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._make_handler())
        except OSError as e:
            raise MapBridgeError(f"지도 연결용 서버를 열지 못했습니다 ({e}).") from e
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def open_window(self, force=False):
        """지도 창을 화면 밖에 엽니다(프로그램 화면에 끼워 넣기 전까지 안 보이게). 이미 열려 있으면 False."""
        self._start_server()
        starting = time.time() - self._launched_at < LAUNCH_GRACE_SEC and self._last_poll < self._launched_at
        if not force and (self.is_open() or starting):
            return False
        browser = next((b for b in _BROWSERS if os.path.exists(b)), None)
        if not browser:
            raise MapBridgeError("Microsoft Edge 또는 Chrome이 있어야 지도를 볼 수 있습니다 (좌표 입력은 그대로 됩니다).")
        os.makedirs(self.profile_dir, exist_ok=True)
        args = [
            browser, f"--app=http://127.0.0.1:{self.port}/{PAGE}",
            "--window-size=1100,820", "--window-position=-4000,-4000",
            f"--user-data-dir={self.profile_dir}", "--no-first-run", "--disable-extensions",
            # 프로그램 창 안에 끼워 넣은 창을 Edge가 '가려진 창'으로 보고 그리기를 쉬지 않게
            "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding",
            "--disable-features=CalculateNativeWinOcclusion",
        ]
        if self.user_agent:
            args.append(f"--user-agent={self.user_agent}")
        subprocess.Popen(args)
        self._launched_at = time.time()
        return True

    def is_open(self):
        return time.time() - self._last_poll < ALIVE_SEC

    def close(self, wait_for_page=True):
        if wait_for_page and self.is_open():
            self._closing = True
            self._close_sent.wait(timeout=ALIVE_SEC)
        if self._server:
            self._server.shutdown()
            self._server = None
