from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import messagebox


APP_NAME = "PaedDeadSpace"
UI_RELEASE = "PaedDeadSpace UI v1.0.0"
CORE_RELEASE = "paeddeadspace 1.0.0"


def bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


BUNDLE_ROOT = bundle_root()
UI_DIR = BUNDLE_ROOT / "ui"
APP_PATH = UI_DIR / "app.py"


def log_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    folder = base / APP_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "PaedDeadSpace.log"


LOG_PATH = log_path()


def write_log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")


def find_free_port(start: int = 8501, stop: int = 8599) -> int:
    for port in range(start, stop + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No free local port available between 8501 and 8599.")


def server_healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/_stcore/health",
            timeout=0.25,
        ) as response:
            return response.status == 200
    except Exception:
        return False


def run_streamlit_server(port: int) -> int:
    if not APP_PATH.exists():
        write_log(f"Fatal: bundled app.py not found at {APP_PATH}")
        return 2

    ui_dir_str = str(UI_DIR)
    if ui_dir_str not in sys.path:
        sys.path.insert(0, ui_dir_str)

    log_handle = LOG_PATH.open("a", encoding="utf-8", buffering=1)
    sys.stdout = log_handle
    sys.stderr = log_handle

    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    write_log(
        f"Starting bundled Streamlit server; UI={UI_RELEASE}; "
        f"core={CORE_RELEASE}; port={port}; developmentMode=false"
    )

    try:
        from streamlit.web.cli import main as streamlit_main

        sys.argv = [
            "streamlit",
            "run",
            str(APP_PATH),
            "--global.developmentMode=false",
            "--server.address=127.0.0.1",
            f"--server.port={port}",
            "--server.headless=true",
            "--server.fileWatcherType=none",
            "--server.runOnSave=false",
            "--browser.gatherUsageStats=false",
        ]
        result = streamlit_main()
        return int(result or 0)
    except BaseException as exc:
        write_log(f"Fatal Streamlit exception: {exc!r}")
        return 3


class Controller:
    def __init__(self, root: tk.Tk, process: subprocess.Popen, port: int) -> None:
        self.root = root
        self.process = process
        self.port = port
        self.url = f"http://127.0.0.1:{port}"
        self.opened_once = False

        root.title(APP_NAME)
        root.geometry("470x225")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.close)

        tk.Label(root, text="PaedDeadSpace", font=("Segoe UI", 18, "bold")).pack(
            pady=(18, 2)
        )
        tk.Label(
            root,
            text="Pediatric apparatus dead-space explorer",
            font=("Segoe UI", 10),
        ).pack()

        self.status = tk.StringVar(value="Starting local application…")
        tk.Label(root, textvariable=self.status, font=("Segoe UI", 10)).pack(
            pady=(18, 8)
        )

        self.open_button = tk.Button(
            root,
            text="Open PaedDeadSpace",
            width=22,
            state="disabled",
            command=self.open_browser,
        )
        self.open_button.pack(pady=3)

        tk.Button(root, text="Exit", width=22, command=self.close).pack(pady=3)

        tk.Label(
            root,
            text=f"{UI_RELEASE}  |  {CORE_RELEASE}\nLocal runtime — no external API",
            font=("Segoe UI", 8),
        ).pack(pady=(12, 0))

        root.after(250, self.poll)

    def open_browser(self) -> None:
        webbrowser.open(self.url)

    def poll(self) -> None:
        if self.process.poll() is not None:
            self.status.set("The local server stopped unexpectedly.")
            self.open_button.config(state="disabled")
            messagebox.showerror(
                APP_NAME,
                "PaedDeadSpace could not start.\n\n"
                f"Diagnostic log:\n{LOG_PATH}",
            )
            return

        if server_healthy(self.port):
            self.status.set(f"Running locally at {self.url}")
            self.open_button.config(state="normal")
            if not self.opened_once:
                self.opened_once = True
                self.open_browser()
            self.root.after(1000, self.poll)
        else:
            self.status.set("Starting local application…")
            self.root.after(250, self.poll)

    def close(self) -> None:
        try:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
        finally:
            self.root.destroy()


def run_controller() -> int:
    port = find_free_port()
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    command = [
        sys.executable,
        "--paeddeadspace-server",
        str(port),
    ]

    env = os.environ.copy()
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    write_log(f"Launching server child on port {port}")
    process = subprocess.Popen(command, env=env, creationflags=flags)

    root = tk.Tk()
    Controller(root, process, port)
    root.mainloop()
    return 0


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--paeddeadspace-server":
        try:
            port = int(sys.argv[2])
        except ValueError:
            write_log("Invalid server port argument.")
            return 4
        return run_streamlit_server(port)

    try:
        return run_controller()
    except BaseException as exc:
        write_log(f"Fatal launcher exception: {exc!r}")
        try:
            messagebox.showerror(
                APP_NAME,
                "PaedDeadSpace could not start.\n\n"
                f"Diagnostic log:\n{LOG_PATH}",
            )
        except Exception:
            pass
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
