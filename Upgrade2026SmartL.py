#!/usr/bin/env python3
"""
Upgrade2026_Smart.py - Smart Version Checker & Tool Manager
Linux Mint edition.
Features: Slither, Echidna, Medusa, Halmos, Foundry version management with native rich UI.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import requests
import json
import os
import sys
import logging
import re
import tempfile, tarfile, zipfile, shutil
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict, List
import threading
from dataclasses import dataclass
from packaging import version


# ==================== Linux PATH Fix ====================
_extra_paths = [
    os.path.expanduser('~/go/bin'),
    os.path.expanduser('~/.local/bin'),
    os.path.expanduser('~/.foundry/bin'),
    '/usr/local/go/bin',
]
for _p in _extra_paths:
    if _p not in os.environ.get('PATH', ''):
        os.environ['PATH'] = _p + ':' + os.environ.get('PATH', '')


# ==================== Configuration ====================

CONFIG = {
    'tools_dir': os.path.expanduser('~/tools/fuzzers'),
    'go_bin':    os.path.expanduser('~/go/bin'),
    'use_go_bin_for_medusa': True,
}

LOG_DIR  = Path('/tmp')
LOG_FILE = LOG_DIR / 'Upgrade2026_Smart.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


# ==================== Data Models ====================

@dataclass
class ToolStatus:
    name: str
    current_version: str
    latest_version: str
    update_available: bool
    status: str

    @property
    def status_symbol(self) -> str:
        return "⚠ " if self.update_available else "✓ "


# ==================== Version Comparison ====================

def compare_versions(current: str, latest: str) -> bool:
    if current in ("not installed", "error"):
        return True
    if latest in ("error", "not found"):
        return False
    current_clean = current.lstrip('v').rstrip('.0')
    latest_clean  = latest.lstrip('v').rstrip('.0')
    if current_clean == latest_clean:
        return False
    try:
        curr_parts   = [int(x) for x in current_clean.split('.') if x.isdigit()]
        latest_parts = [int(x) for x in latest_clean.split('.')  if x.isdigit()]
        max_len = max(len(curr_parts), len(latest_parts))
        curr_parts.extend([0]   * (max_len - len(curr_parts)))
        latest_parts.extend([0] * (max_len - len(latest_parts)))
        for curr, lat in zip(curr_parts, latest_parts):
            if lat > curr: return True
            if curr > lat: return False
    except (ValueError, AttributeError):
        return False
    return False


# ==================== Tool Checkers ====================

class ToolChecker:
    @staticmethod
    def run_command(cmd: str) -> str:
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=5)
            return result.stdout + result.stderr
        except Exception as e:
            logger.error(f"Command failed: {cmd} - {e}")
            return ""


class SlitherChecker(ToolChecker):
    @staticmethod
    def get_local_version() -> str:
        try:
            output = SlitherChecker.run_command("slither --version")
            if output:
                match = re.search(r'(\d+\.\d+\.\d+)', output)
                return match.group(1) if match else "not installed"
        except Exception:
            pass
        return "not installed"

    @staticmethod
    def get_latest_version() -> str:
        try:
            response = requests.get("https://pypi.org/pypi/slither-analyzer/json", timeout=5)
            return response.json()['info']['version']
        except Exception as e:
            logger.error(f"Failed to fetch Slither version: {e}")
            return "error"

    @staticmethod
    def update() -> bool:
        try:
            result = subprocess.run(
                ["python3", "-m", "pip", "install", "--upgrade",
                 "slither-analyzer", "--break-system-packages"],
                capture_output=True, text=True, timeout=60)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Slither update failed: {e}")
            return False


class EchidnaChecker(ToolChecker):
    @staticmethod
    def get_local_version() -> str:
        try:
            output = EchidnaChecker.run_command("echidna --version")
            if output:
                match = re.search(r'Echidna\s+([^\s\(]+)', output)
                return match.group(1).strip() if match else "not installed"
        except Exception:
            pass
        return "not installed"

    @staticmethod
    def get_latest_version() -> str:
        try:
            response = requests.get(
                "https://api.github.com/repos/crytic/echidna/releases/latest",
                headers={"User-Agent": "Python"}, timeout=5)
            return response.json()['tag_name'].lstrip('v')
        except Exception as e:
            logger.error(f"Failed to fetch Echidna version: {e}")
            return "error"

    @staticmethod
    def update() -> bool:
        try:
            response = requests.get(
                "https://api.github.com/repos/crytic/echidna/releases/latest",
                headers={"User-Agent": "Python"}, timeout=5)
            assets = response.json()['assets']
            asset = next(
                (a for a in assets
                 if any(x in a['name'].lower() for x in ['linux', 'x86_64', 'amd64'])
                 and a['name'].endswith(('.tar.gz', '.zip', '.AppImage'))),
                None
            )
            if not asset:
                logger.error("Linux build not found for Echidna")
                return False
            download_url = asset['browser_download_url']
            filename     = asset['name']
            install_dir  = os.path.expanduser('~/.local/bin')
            os.makedirs(install_dir, exist_ok=True)
            logger.info(f"Downloading Echidna from {download_url}")
            with tempfile.TemporaryDirectory() as tmp:
                tmp_file = os.path.join(tmp, filename)
                dl = requests.get(download_url, timeout=120)
                with open(tmp_file, 'wb') as f:
                    f.write(dl.content)
                if filename.endswith('.tar.gz'):
                    with tarfile.open(tmp_file, 'r:gz') as tar:
                        tar.extractall(tmp)
                elif filename.endswith('.zip'):
                    with zipfile.ZipFile(tmp_file, 'r') as z:
                        z.extractall(tmp)
                elif filename.endswith('.AppImage'):
                    dst = os.path.join(install_dir, 'echidna')
                    shutil.copy2(tmp_file, dst)
                    os.chmod(dst, 0o755)
                    return True
                for root_dir, dirs, files in os.walk(tmp):
                    for f in files:
                        if f in ('echidna', 'echidna-test'):
                            src = os.path.join(root_dir, f)
                            dst = os.path.join(install_dir, 'echidna')
                            shutil.copy2(src, dst)
                            os.chmod(dst, 0o755)
                            return True
            logger.error("echidna binary not found in archive")
            return False
        except Exception as e:
            logger.error(f"Echidna update failed: {e}")
            return False


class MedusaChecker(ToolChecker):
    @staticmethod
    def get_local_version() -> str:
        try:
            output = MedusaChecker.run_command("medusa --version")
            if output:
                match = re.search(r'version\s+(v?[^\s]+)', output)
                return match.group(1).lstrip('v') if match else "not installed"
        except Exception:
            pass
        return "not installed"

    @staticmethod
    def get_latest_version() -> str:
        try:
            response = requests.get(
                "https://api.github.com/repos/crytic/medusa/releases/latest",
                headers={"User-Agent": "Python"}, timeout=5)
            return response.json()['tag_name'].lstrip('v')
        except Exception as e:
            logger.error(f"Failed to fetch Medusa version: {e}")
            return "error"

    @staticmethod
    def update() -> bool:
        try:
            result = subprocess.run(
                ["go", "install", "github.com/crytic/medusa@latest"],
                capture_output=True, text=True, timeout=120)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Medusa update failed: {e}")
            return False


class HalmosChecker(ToolChecker):
    @staticmethod
    def get_local_version() -> str:
        try:
            output = HalmosChecker.run_command("halmos --version")
            if output:
                match = re.search(r'(\d+\.\d+\.\d+)', output)
                return match.group(1) if match else output.strip()
        except Exception:
            pass
        return "not installed"

    @staticmethod
    def get_latest_version() -> str:
        try:
            response = requests.get("https://pypi.org/pypi/halmos/json", timeout=5)
            return response.json()['info']['version']
        except Exception as e:
            logger.error(f"Failed to fetch Halmos version: {e}")
            return "error"

    @staticmethod
    def update() -> bool:
        try:
            result = subprocess.run(
                ["python3", "-m", "pip", "install", "--upgrade",
                 "halmos", "--break-system-packages"],
                capture_output=True, text=True, timeout=60)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Halmos update failed: {e}")
            return False


class FoundryChecker(ToolChecker):
    """Check and update Foundry (forge/cast/anvil toolkit)."""

    @staticmethod
    def get_local_version() -> str:
        try:
            output = FoundryChecker.run_command("forge --version")
            if output:
                # e.g. "forge 0.2.0 (abc1234 2024-01-01T...)"
                match = re.search(r'forge\s+(\S+)', output, re.IGNORECASE)
                return match.group(1) if match else "not installed"
        except Exception:
            pass
        return "not installed"

    @staticmethod
    def get_latest_version() -> str:
        try:
            response = requests.get(
                "https://api.github.com/repos/foundry-rs/foundry/releases/latest",
                headers={"User-Agent": "Python"}, timeout=5)
            tag = response.json().get('tag_name', '')
            return tag.lstrip('v') if tag else "error"
        except Exception as e:
            logger.error(f"Failed to fetch Foundry version: {e}")
            return "error"

    @staticmethod
    def update() -> bool:
        """Update via foundryup (official installer)."""
        try:
            foundryup = os.path.expanduser('~/.foundry/bin/foundryup')
            if os.path.exists(foundryup):
                result = subprocess.run(
                    [foundryup], capture_output=True, text=True, timeout=120)
                return result.returncode == 0
            else:
                logger.info("foundryup not found — installing via curl")
                result = subprocess.run(
                    "curl -L https://foundry.paradigm.xyz | bash",
                    shell=True, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    result2 = subprocess.run(
                        [os.path.expanduser('~/.foundry/bin/foundryup')],
                        capture_output=True, text=True, timeout=120)
                    return result2.returncode == 0
                return False
        except Exception as e:
            logger.error(f"Foundry update failed: {e}")
            return False


# ==================== Main GUI Application ====================

class ModernScrollbar(ttk.Scrollbar):
    pass


class Upgrade2026App:
    TOOLS = {
        'Slither': SlitherChecker,
        'Echidna': EchidnaChecker,
        'Medusa':  MedusaChecker,
        'Halmos':  HalmosChecker,
        'Foundry': FoundryChecker,
    }

    COLORS = {
        'bg_primary':   '#0f1419',
        'bg_secondary': '#1a1f2e',
        'bg_tertiary':  '#252b3d',
        'accent_primary':  '#00d9ff',
        'accent_warning':  '#ffa500',
        'accent_success':  '#00ff41',
        'accent_error':    '#ff3333',
        'text_primary':    '#e0e0e0',
        'text_secondary':  '#a0a0a0',
        'border':          '#2a3147',
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Security Tools Upgrade Manager")
        self.root.geometry("1200x780")
        self.root.configure(bg=self.COLORS['bg_primary'])
        style = ttk.Style()
        style.theme_use('clam')
        self.configure_styles(style)
        self.tools_status: Dict[str, ToolStatus] = {}
        self.selected_for_update = set()
        self.is_updating = False
        self.build_ui()
        self.center_window()
        logger.info("Application started")

    def configure_styles(self, style: ttk.Style):
        style.configure('TFrame', background=self.COLORS['bg_primary'])
        style.configure('TLabel', background=self.COLORS['bg_primary'],
                        foreground=self.COLORS['text_primary'])
        style.configure('Title.TLabel',  font=('Ubuntu', 16, 'bold'),
                        background=self.COLORS['bg_primary'],
                        foreground=self.COLORS['accent_primary'])
        style.configure('Header.TLabel', font=('Ubuntu', 11, 'bold'),
                        background=self.COLORS['bg_secondary'],
                        foreground=self.COLORS['text_primary'])
        style.configure('Primary.TButton', font=('Ubuntu', 10))
        style.map('Primary.TButton',
                  foreground=[('pressed', self.COLORS['bg_primary'])],
                  background=[('pressed', self.COLORS['accent_primary'])])
        style.configure('Treeview',
                        background=self.COLORS['bg_secondary'],
                        foreground=self.COLORS['text_primary'],
                        fieldbackground=self.COLORS['bg_secondary'], borderwidth=0)
        style.configure('Treeview.Heading',
                        background=self.COLORS['bg_tertiary'],
                        foreground=self.COLORS['accent_primary'], borderwidth=1)
        style.map('Treeview',
                  background=[('selected', self.COLORS['bg_tertiary'])],
                  foreground=[('selected', self.COLORS['accent_primary'])])

    def center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth()  // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def build_ui(self):
        main_frame = tk.Frame(self.root, bg=self.COLORS['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        self.build_header(main_frame)
        self.build_status_bar(main_frame)
        self.build_tools_table(main_frame)
        self.build_log_area(main_frame)
        self.build_controls(main_frame)
        self.build_status_indicator(main_frame)

    def build_header(self, parent):
        hf = tk.Frame(parent, bg=self.COLORS['bg_secondary'], relief=tk.FLAT)
        hf.pack(fill=tk.X, padx=0, pady=5, ipady=12)
        hi = tk.Frame(hf, bg=self.COLORS['bg_secondary'])
        hi.pack(fill=tk.X, padx=15)
        tk.Label(hi, text="🔐 Security Tools Manager",
                 font=('Ubuntu', 18, 'bold'),
                 bg=self.COLORS['bg_secondary'],
                 fg=self.COLORS['accent_primary']).pack(side=tk.LEFT)
        tk.Label(hi, text="Smart version checker for Slither, Echidna, Medusa, Halmos & Foundry",
                 font=('Ubuntu', 9),
                 bg=self.COLORS['bg_secondary'],
                 fg=self.COLORS['text_secondary']).pack(side=tk.LEFT, padx=20)

    def build_status_bar(self, parent):
        sf = tk.Frame(parent, bg=self.COLORS['bg_primary'])
        sf.pack(fill=tk.X, padx=0, pady=5)
        tl = tk.Label(sf, text="", font=('Ubuntu', 9),
                      bg=self.COLORS['bg_primary'],
                      fg=self.COLORS['text_secondary'])
        tl.pack(side=tk.LEFT)
        def update_time():
            tl.config(text=f"📅 {datetime.now().strftime('%A, %d %B %Y - %H:%M:%S')}")
            self.root.after(1000, update_time)
        update_time()

    def build_tools_table(self, parent):
        table_frame = tk.Frame(parent, bg=self.COLORS['bg_secondary'], relief=tk.FLAT)
        table_frame.pack(fill=tk.BOTH, expand=False, padx=0, pady=5)
        header = tk.Frame(table_frame, bg=self.COLORS['bg_tertiary'])
        header.pack(fill=tk.X)
        for hdr_text, width in zip(
            ['Tool', 'Current Version', 'Latest Version', 'Update Available', 'Status', 'Update?'],
            [100,    150,                150,              130,                180,       80]
        ):
            tk.Label(header, text=hdr_text, width=width // 8,
                     font=('Ubuntu', 10, 'bold'),
                     bg=self.COLORS['bg_tertiary'],
                     fg=self.COLORS['accent_primary'],
                     padx=10, pady=10).pack(side=tk.LEFT, fill=tk.X)
        self.tools_frame = tk.Frame(table_frame, bg=self.COLORS['bg_secondary'])
        self.tools_frame.pack(fill=tk.BOTH, expand=False)
        self.tool_widgets = {}
        for tool_name in self.TOOLS:
            self.create_tool_row(self.tools_frame, tool_name)

    def create_tool_row(self, parent, tool_name):
        row = tk.Frame(parent, bg=self.COLORS['bg_secondary'], relief=tk.FLAT)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=tool_name, width=12,
                 font=('Ubuntu', 10),
                 bg=self.COLORS['bg_secondary'],
                 fg=self.COLORS['accent_primary'],
                 padx=10, pady=8, anchor='w').pack(side=tk.LEFT, fill=tk.X)
        cur = tk.Label(row, text="Checking...", width=18,
                       font=('Courier New', 9),
                       bg=self.COLORS['bg_secondary'],
                       fg=self.COLORS['text_primary'],
                       padx=10, pady=8, anchor='w')
        cur.pack(side=tk.LEFT, fill=tk.X)
        lat = tk.Label(row, text="Checking...", width=18,
                       font=('Courier New', 9),
                       bg=self.COLORS['bg_secondary'],
                       fg=self.COLORS['text_primary'],
                       padx=10, pady=8, anchor='w')
        lat.pack(side=tk.LEFT, fill=tk.X)
        upd = tk.Label(row, text="—", width=15,
                       font=('Ubuntu', 9),
                       bg=self.COLORS['bg_secondary'],
                       fg=self.COLORS['text_secondary'],
                       padx=10, pady=8, anchor='w')
        upd.pack(side=tk.LEFT, fill=tk.X)
        sta = tk.Label(row, text="Checking...", width=21,
                       font=('Ubuntu', 9),
                       bg=self.COLORS['bg_secondary'],
                       fg=self.COLORS['text_secondary'],
                       padx=10, pady=8, anchor='w')
        sta.pack(side=tk.LEFT, fill=tk.X)
        var = tk.BooleanVar()
        chk = tk.Checkbutton(row, variable=var,
                             bg=self.COLORS['bg_secondary'],
                             fg=self.COLORS['accent_primary'],
                             selectcolor=self.COLORS['bg_tertiary'],
                             activebackground=self.COLORS['bg_secondary'],
                             activeforeground=self.COLORS['accent_primary'],
                             padx=10, pady=8)
        chk.pack(side=tk.LEFT, fill=tk.X)
        self.tool_widgets[tool_name] = {
            'row': row, 'current': cur, 'latest': lat,
            'update_avail': upd, 'status': sta,
            'checkbox': chk, 'var': var
        }

    def build_log_area(self, parent):
        tk.Label(parent, text="Operation Log",
                 font=('Ubuntu', 10, 'bold'),
                 bg=self.COLORS['bg_primary'],
                 fg=self.COLORS['text_primary'],
                 pady=5).pack(anchor='w')
        lf = tk.Frame(parent, bg=self.COLORS['bg_secondary'],
                      relief=tk.FLAT, highlightthickness=1,
                      highlightbackground=self.COLORS['border'])
        lf.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_box = scrolledtext.ScrolledText(
            lf, height=8, font=('Courier New', 8),
            bg=self.COLORS['bg_tertiary'], fg=self.COLORS['text_primary'],
            insertbackground=self.COLORS['accent_primary'],
            relief=tk.FLAT, padx=10, pady=10)
        self.log_box.pack(fill=tk.BOTH, expand=True)
        self.log_box.tag_config('info',    foreground=self.COLORS['accent_primary'])
        self.log_box.tag_config('warning', foreground=self.COLORS['accent_warning'])
        self.log_box.tag_config('error',   foreground=self.COLORS['accent_error'])
        self.log_box.tag_config('success', foreground=self.COLORS['accent_success'])

    def build_controls(self, parent):
        bf = tk.Frame(parent, bg=self.COLORS['bg_primary'])
        bf.pack(fill=tk.X, pady=5)
        for text, cmd, color in [
            ("🔄 Check Versions",  self.refresh_versions, self.COLORS['accent_primary']),
            ("⬆️  Update Selected", self.update_selected,  self.COLORS['accent_warning']),
            ("⚡ Update All",       self.update_all,        self.COLORS['accent_error']),
            ("🗑️  Clear Log",       self.clear_log,         self.COLORS['text_secondary']),
        ]:
            tk.Button(bf, text=text, command=cmd,
                      font=('Ubuntu', 10, 'bold'), bg=color,
                      fg=self.COLORS['bg_primary'] if color != self.COLORS['text_secondary'] else self.COLORS['text_primary'],
                      relief=tk.FLAT, padx=15, pady=8, cursor='hand2',
                      activebackground=color,
                      activeforeground=self.COLORS['bg_primary']).pack(side=tk.LEFT, padx=5)

    def build_status_indicator(self, parent):
        self.status_frame = tk.Frame(parent, bg=self.COLORS['bg_primary'])
        self.status_frame.pack(fill=tk.X, pady=3)
        self.status_indicator = tk.Label(
            self.status_frame, text="✓ Ready",
            font=('Ubuntu', 9),
            bg=self.COLORS['bg_primary'],
            fg=self.COLORS['accent_success'])
        self.status_indicator.pack(anchor='w')

    # ── Logic ──────────────────────────────────────────────────────────

    def update_log(self, message: str, level: str = 'info'):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert(tk.END, f"[{ts}] {message}\n", level)
        self.log_box.see(tk.END)
        logger.log(
            logging.INFO    if level == 'info'    else
            logging.WARNING if level == 'warning' else
            logging.ERROR, message)

    def set_status(self, message: str, status_type: str = 'ready'):
        colors  = {'ready': self.COLORS['accent_success'],
                   'updating': self.COLORS['accent_warning'],
                   'error': self.COLORS['accent_error']}
        symbols = {'ready': '✓', 'updating': '⏳', 'error': '✗'}
        self.status_indicator.config(
            text=f"{symbols.get(status_type, '•')} {message}",
            fg=colors.get(status_type, self.COLORS['text_primary']))

    def refresh_versions(self):
        def check_versions():
            self.set_status("Checking versions...", 'updating')
            self.update_log("Checking versions for all tools...", 'info')
            for tool_name, checker_class in self.TOOLS.items():
                try:
                    current      = checker_class.get_local_version()
                    latest       = checker_class.get_latest_version()
                    needs_update = compare_versions(current, latest)
                    self.tools_status[tool_name] = ToolStatus(
                        name=tool_name, current_version=current,
                        latest_version=latest, update_available=needs_update,
                        status="⚠ Update available" if needs_update else "✓ Up to date")
                    self.update_tool_row(tool_name)
                    self.update_log(
                        f"{tool_name}: {current} → {latest if needs_update else '✓ latest'}",
                        'info')
                except Exception as e:
                    self.update_log(f"Error checking {tool_name}: {e}", 'error')
            self.set_status("Version check completed", 'ready')
            self.update_log("Version check completed", 'success')
        threading.Thread(target=check_versions, daemon=True).start()

    def update_tool_row(self, tool_name: str):
        if tool_name not in self.tools_status or tool_name not in self.tool_widgets:
            return
        status  = self.tools_status[tool_name]
        widgets = self.tool_widgets[tool_name]
        widgets['current'].config(text=status.current_version)
        widgets['latest'].config(text=status.latest_version)
        if status.update_available:
            widgets['update_avail'].config(text="YES", fg=self.COLORS['accent_warning'])
            widgets['status'].config(text="Update available", fg=self.COLORS['accent_warning'])
            widgets['var'].set(True)
        else:
            widgets['update_avail'].config(text="No",  fg=self.COLORS['accent_success'])
            widgets['status'].config(text="Up to date", fg=self.COLORS['accent_success'])
            widgets['var'].set(False)

    def update_selected(self):
        selected = [n for n, w in self.tool_widgets.items() if w['var'].get()]
        if not selected:
            messagebox.showinfo("Info", "Please select tools to update")
            self.update_log("No tools selected", 'warning')
            return
        def do_update():
            self.is_updating = True
            self.set_status("Updating selected tools...", 'updating')
            self.update_log(f"Starting update of {len(selected)} tool(s)...", 'info')
            updated_count = 0
            for tool_name in selected:
                try:
                    if self.TOOLS[tool_name].update():
                        updated_count += 1
                        self.update_log(f"✓ {tool_name} updated successfully", 'success')
                    else:
                        self.update_log(f"✗ Failed to update {tool_name}", 'error')
                except Exception as e:
                    self.update_log(f"Error updating {tool_name}: {e}", 'error')
            self.refresh_versions()
            self.is_updating = False
            self.update_log(
                f"Update completed. Tools updated: {updated_count}/{len(selected)}", 'success')
            self.set_status(f"Updated {updated_count} tool(s)", 'ready')
        threading.Thread(target=do_update, daemon=True).start()

    def update_all(self):
        if messagebox.askyesno("Confirm", "Update all tools?"):
            self.update_log("Starting update of all tools...", 'warning')
            for widget in self.tool_widgets.values():
                widget['var'].set(True)
            self.update_selected()

    def clear_log(self):
        self.log_box.delete(1.0, tk.END)
        self.update_log("Log cleared", 'info')


def main():
    root = tk.Tk()
    app  = Upgrade2026App(root)
    root.after(500, app.refresh_versions)
    root.mainloop()


if __name__ == '__main__':
    main()
