#!/usr/bin/env python3
"""boomer end-to-end setup for Windows, macOS and Linux.

Installs everything boomer shells out to:

    base      bash, curl, git, jq
    scanners  anew, subfinder, assetfinder, subdominator (Python 3.13+),
              httpx-toolkit
    headless  Node.js 18+ + endpoint-finder + Playwright Chromium
              Python 3.9+ + techdetect + Playwright Chromium
    boomer    this repo's boomer script on PATH

Usage:
    sudo python3 setup.py --setup      # full install (macOS/Linux)
    python  setup.py --setup           # full install (Windows / no sudo)
    python3 setup.py --check           # show what is installed, change nothing
    python3 setup.py --help

The script is idempotent: anything already on PATH is left alone unless
--force is given. On Linux it uses apt/dnf/yum/pacman/zypper/apk; on macOS
Homebrew; on Windows winget (choco/scoop as fallback).

Links:
    https://github.com/Raunaksplanet/boomer
    https://github.com/Raunaksplanet/endpoint-finder
    https://github.com/Raunaksplanet/techdetect
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Dict, List, Optional, Sequence

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")
MIN_PYTHON = (3, 8)
SUBDOMINATOR_PYTHON = (3, 13)

ENDPOINT_FINDER_REPO = "https://github.com/Raunaksplanet/endpoint-finder"
TECHDETECT_REPO = "https://github.com/Raunaksplanet/techdetect"

# (module, binary) installed with `go install`.
GO_TOOLS = [
    ("github.com/tomnomnom/anew@latest", "anew"),
    ("github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest", "subfinder"),
    ("github.com/tomnomnom/assetfinder@latest", "assetfinder"),
    ("github.com/projectdiscovery/httpx/cmd/httpx@latest", "httpx"),
]

# bin name -> human label, used by --check and the final verification.
REQUIRED_BINS = [
    ("bash", "bash (runs the boomer script)"),
    ("curl", "curl"),
    ("git", "git"),
    ("jq", "jq"),
    ("go", "Go toolchain"),
    ("node", "Node.js 18+"),
    ("npm", "npm"),
    ("anew", "anew"),
    ("subfinder", "subfinder"),
    ("assetfinder", "assetfinder"),
    ("subdominator", "subdominator"),
    ("httpx-toolkit", "httpx-toolkit"),
    ("endpoint-finder", "endpoint-finder"),
    ("techdetect", "techdetect"),
]

DRY_RUN = False
VERBOSE = False
IS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0
SUDO_USER = os.environ.get("SUDO_USER") if IS_ROOT else None
USER_HOME = os.path.expanduser("~")


# --------------------------------------------------------------------------
# logging
# --------------------------------------------------------------------------
def _color(code: str, text: str) -> str:
    if sys.stdout.isatty() and not IS_WINDOWS:
        return "\033[%sm%s\033[0m" % (code, text)
    return text


def log(msg: str) -> None:
    print(_color("1;34", "[*]") + " " + msg, flush=True)


def ok(msg: str) -> None:
    print(_color("1;32", "[OK]") + " " + msg, flush=True)


def warn(msg: str) -> None:
    print(_color("1;33", "[WARN]") + " " + msg, flush=True)


def fail(msg: str) -> None:
    print(_color("1;31", "[ERROR]") + " " + msg, file=sys.stderr, flush=True)


def info(msg: str) -> None:
    print(_color("1;36", "[INFO]") + " " + msg, flush=True)


# --------------------------------------------------------------------------
# process helpers
# --------------------------------------------------------------------------
def _resolve(path: str) -> str:
    found = shutil.which(path)
    return found or path


def _windows_resolve(cmd: List[str]) -> List[str]:
    """Windows can only CreateProcess .exe directly; .cmd/.bat need cmd /c."""
    if not IS_WINDOWS or not cmd:
        return cmd
    exe = shutil.which(cmd[0])
    if exe:
        cmd[0] = exe
        if exe.lower().endswith((".cmd", ".bat")):
            cmd = ["cmd", "/c"] + cmd
    return cmd


def run(
    cmd: Sequence[str],
    desc: str,
    check: bool = True,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
) -> int:
    cmd = _windows_resolve([str(c) for c in cmd])
    log(desc)
    if VERBOSE:
        print("    $ " + " ".join(cmd), flush=True)
    if DRY_RUN:
        return 0
    try:
        proc = subprocess.run(cmd, env=env, cwd=cwd)
        rc = proc.returncode
    except FileNotFoundError:
        rc = 127
        fail("command not found: %s" % cmd[0])
    except KeyboardInterrupt:
        raise
    if check and rc != 0:
        fail("%s failed (exit %d)" % (desc, rc))
        raise SystemExit(rc)
    return rc


def capture(cmd: Sequence[str], as_user: bool = False) -> str:
    """Run a command and return stripped stdout (empty string on failure)."""
    cmd = [str(c) for c in cmd]
    if as_user and IS_ROOT and SUDO_USER and SUDO_USER != "root":
        cmd = ["sudo", "-u", SUDO_USER, "-H", "env", "PATH=" + os.environ.get("PATH", "")] + cmd
    cmd = _windows_resolve(cmd)
    if DRY_RUN:
        return ""
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    except (FileNotFoundError, OSError):
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def user_run(cmd: Sequence[str], desc: str, check: bool = True,
             env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None) -> int:
    """Run as the invoking user (drops sudo for brew/npm/pip/go)."""
    if IS_ROOT and SUDO_USER and SUDO_USER != "root":
        full = ["sudo", "-u", SUDO_USER, "-H", "env", "PATH=" + os.environ.get("PATH", "")] + list(cmd)
        return run(full, desc, check=check, env=env, cwd=cwd)
    return run(cmd, desc, check=check, env=env, cwd=cwd)


def admin_run(cmd: Sequence[str], desc: str, check: bool = True) -> int:
    """Run with root; prefix sudo when the caller is not root."""
    if IS_WINDOWS or IS_ROOT:
        return run(cmd, desc, check=check)
    return run(["sudo"] + list(cmd), desc, check=check)


def which(name: str) -> Optional[str]:
    return shutil.which(name)


def have(name: str) -> bool:
    return which(name) is not None


def prepend_path(directory: str) -> None:
    if not directory:
        return
    directory = os.path.abspath(directory)
    parts = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
    if directory not in parts:
        os.environ["PATH"] = directory + os.pathsep + os.environ.get("PATH", "")


def major_version(text: str) -> int:
    digits = ""
    for ch in text:
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    return int(digits) if digits else 0


# --------------------------------------------------------------------------
# PATH discovery / persistence
# --------------------------------------------------------------------------
def augment_path() -> None:
    """Make tools installed for the invoking user visible to this process."""
    # user login PATH (finds nvm/npm/pyenv/brew installed by the user)
    if IS_ROOT and SUDO_USER and SUDO_USER != "root":
        shell_path = capture(["sudo", "-u", SUDO_USER, "-H", "bash", "-lc", 'printf %s "$PATH"'])
        for part in reversed([p for p in shell_path.split(os.pathsep) if p]):
            prepend_path(part)
    for directory in (
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
        os.path.join(USER_HOME, ".local", "bin"),
        os.path.join(USER_HOME, "go", "bin"),
        os.path.join(USER_HOME, ".cargo", "bin"),
    ):
        if os.path.isdir(directory):
            prepend_path(directory)
    if IS_WINDOWS:
        program_files = os.environ.get("ProgramFiles", "")
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(os.environ.get("APPDATA", ""), "npm"),
            os.path.join(local_appdata, "Programs", "Python"),
            os.path.join(USER_HOME, "go", "bin"),
            os.path.join(USER_HOME, ".local", "bin"),
            os.path.join(program_files, "Git", "bin"),
            os.path.join(program_files, "Git", "cmd"),
            os.path.join(program_files, "nodejs"),
            os.path.join(program_files, "Go", "bin"),
            os.path.join(USER_HOME, "scoop", "shims"),
            os.path.join(os.environ.get("ProgramData", ""), "chocolatey", "bin"),
        ]
        try:
            import glob
            for py_dir in glob.glob(os.path.join(local_appdata, "Programs", "Python", "Python3*")):
                candidates.append(py_dir)
                candidates.append(os.path.join(py_dir, "Scripts"))
        except OSError:
            pass
        for directory in candidates:
            if directory and os.path.isdir(directory):
                prepend_path(directory)


def add_path_unix(directory: str) -> None:
    if not directory:
        return
    if DRY_RUN:
        log("would add PATH entry for " + directory)
        return
    home = USER_HOME
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell or (not shell and IS_MAC):
        shells = [os.path.join(home, ".zshrc"), os.path.join(home, ".zprofile")]
    else:
        shells = [os.path.join(home, ".bashrc"), os.path.join(home, ".profile")]
    line = 'export PATH="%s:$PATH"  # boomer setup' % directory
    for rc in shells:
        try:
            content = ""
            if os.path.exists(rc):
                with open(rc, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            if line in content:
                continue
            with open(rc, "a", encoding="utf-8") as fh:
                if content and not content.endswith("\n"):
                    fh.write("\n")
                fh.write(line + "\n")
            info("added PATH entry to " + rc)
        except OSError as exc:
            warn("could not update %s (%s)" % (rc, exc))


def add_path_windows(directories: Sequence[str]) -> None:
    dirs = [d for d in directories if d]
    if not dirs:
        return
    if DRY_RUN:
        log("would add to user PATH: " + ";".join(dirs))
        return
    try:
        import winreg
    except ImportError:
        warn("could not update PATH automatically; add: " + ";".join(dirs))
        return
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                         winreg.KEY_READ | winreg.KEY_SET_VALUE)
    try:
        try:
            current, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current = ""
        parts = [p for p in current.split(";") if p]
        lowered = {p.lower() for p in parts}
        added = [d for d in dirs if d.lower() not in lowered]
        if added:
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ,
                              ";".join(parts + added))
            info("added to user PATH: " + ";".join(added))
        for d in dirs:
            prepend_path(d)
    finally:
        key.Close()


def persist_path(directories: Sequence[str]) -> None:
    if IS_WINDOWS:
        add_path_windows(directories)
    else:
        seen = set()
        for d in directories:
            if d and d not in seen:
                seen.add(d)
                add_path_unix(d)


# --------------------------------------------------------------------------
# package managers
# --------------------------------------------------------------------------
def ensure_brew() -> bool:
    if have("brew"):
        return True
    if not IS_MAC:
        return False
    warn("Homebrew not found; installing it (this can take a few minutes)")
    env = os.environ.copy()
    env["NONINTERACTIVE"] = "1"
    user_run(
        ["/bin/bash", "-c",
         'curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | bash'],
        "install Homebrew",
        check=False,
        env=env,
    )
    for prefix in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew"):
        if os.path.exists(prefix):
            prepend_path(os.path.dirname(prefix))
            break
    return have("brew")


def brew_install(packages: Sequence[str]) -> None:
    packages = [p for p in packages if p]
    if not packages:
        return
    if not ensure_brew():
        warn("Homebrew unavailable; install manually: " + " ".join(packages))
        return
    user_run(["brew", "install"] + list(packages), "brew install " + " ".join(packages),
             check=False)


def linux_install_manager() -> Optional[str]:
    for manager in ("apt-get", "dnf", "yum", "pacman", "zypper", "apk"):
        if have(manager):
            return manager
    return None


def pm_packages(manager: str, wanted: Sequence[str]) -> List[str]:
    """Translate generic package keys to distro package names."""
    maps = {
        "apt-get": {"curl": "curl", "git": "git", "jq": "jq", "go": "golang-go",
                    "node": "nodejs", "npm": "npm", "python3": "python3",
                    "pip": "python3-pip", "pipx": "pipx", "build": "build-essential"},
        "dnf": {"curl": "curl", "git": "git", "jq": "jq", "go": "golang",
                "node": "nodejs", "npm": "npm", "python3": "python3",
                "pip": "python3-pip", "pipx": "pipx", "build": "gcc"},
        "yum": {"curl": "curl", "git": "git", "jq": "jq", "go": "golang",
                "node": "nodejs", "npm": "npm", "python3": "python3",
                "pip": "python3-pip", "pipx": "pipx", "build": "gcc"},
        "pacman": {"curl": "curl", "git": "git", "jq": "jq", "go": "go",
                   "node": "nodejs", "npm": "npm", "python3": "python",
                   "pip": "python-pip", "pipx": "python-pipx", "build": "base-devel"},
        "zypper": {"curl": "curl", "git": "git", "jq": "jq", "go": "go",
                   "node": "nodejs", "npm": "npm", "python3": "python3",
                   "pip": "python3-pip", "pipx": "python3-pipx", "build": "gcc"},
        "apk": {"curl": "curl", "git": "git", "jq": "jq", "go": "go",
                "node": "nodejs", "npm": "npm", "python3": "python3",
                "pip": "py3-pip", "pipx": "pipx", "build": "build-base"},
    }
    mapping = maps.get(manager, {})
    return [mapping[k] for k in wanted if k in mapping]


def linux_install(keys: Sequence[str]) -> None:
    keys = [k for k in keys if k]
    if not keys:
        return
    manager = linux_install_manager()
    if not manager:
        warn("no supported package manager found (apt/dnf/yum/pacman/zypper/apk)")
        return
    packages = pm_packages(manager, keys)
    if not packages:
        return
    if manager == "apt-get":
        admin_run(["apt-get", "update", "-y"], "apt-get update", check=False)
        if IS_ROOT:
            run(["env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y"] + packages,
                "apt-get install " + " ".join(packages), check=False)
        else:
            admin_run(["env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y"] + packages,
                      "apt-get install " + " ".join(packages), check=False)
    elif manager in ("dnf", "yum", "zypper"):
        admin_run([manager, "install", "-y"] + packages,
                  manager + " install " + " ".join(packages), check=False)
    elif manager == "pacman":
        admin_run(["pacman", "-Sy", "--noconfirm", "--needed"] + packages,
                  "pacman install " + " ".join(packages), check=False)
    elif manager == "apk":
        admin_run(["apk", "add", "--no-cache"] + packages,
                  "apk add " + " ".join(packages), check=False)


WINGET_IDS = {
    "git": "Git.Git",
    "jq": "jqlang.jq",
    "go": "GoLang.Go",
    "node": "OpenJS.NodeJS.LTS",
    "python3": "Python.Python.3.12",
}


def windows_install(keys: Sequence[str]) -> None:
    if not have("winget"):
        if have("choco"):
            for key in keys:
                name = {"git": "git", "jq": "jq", "go": "golang",
                        "node": "nodejs-lts", "python3": "python3"}.get(key)
                if name:
                    admin_run(["choco", "install", name, "-y"],
                              "choco install " + name, check=False)
            return
        warn("winget/choco not found; install these manually: " + ", ".join(keys))
        return
    for key in keys:
        package = WINGET_IDS.get(key)
        if not package:
            continue
        admin_run(["winget", "install", "--id", package, "-e", "--silent",
                   "--accept-package-agreements", "--accept-source-agreements"],
                  "winget install " + package, check=False)


def ensure_base_tools(force: bool = False) -> None:
    wanted = []
    for key, binary in (("curl", "curl"), ("git", "git"), ("jq", "jq"),
                        ("go", "go"), ("node", "node"), ("python3", "python3")):
        if force or not have(binary):
            wanted.append(key)
    if not wanted:
        ok("base tools already present")
        return
    if IS_MAC:
        brew_install(wanted)
    elif IS_LINUX:
        linux_install(wanted)
    elif IS_WINDOWS:
        windows_install(wanted)
    # refresh common locations
    augment_path()


# --------------------------------------------------------------------------
# individual tools
# --------------------------------------------------------------------------
def go_bin_dir() -> str:
    gopath = capture(["go", "env", "GOPATH"], as_user=True)
    if not gopath:
        gopath = os.path.join(USER_HOME, "go")
    return os.path.join(gopath, "bin")


def install_go_tools(force: bool) -> None:
    if not have("go"):
        warn("Go is not available; skipping anew/subfinder/assetfinder/httpx")
        return
    for module, binary in GO_TOOLS:
        if have(binary) and not force:
            ok("%s already installed" % binary)
            continue
        user_run(["go", "install", module], "go install " + binary, check=False)
    bin_dir = go_bin_dir()
    if os.path.isdir(bin_dir):
        prepend_path(bin_dir)
    # boomer calls the ProjectDiscovery binary "httpx-toolkit" so it never
    # collides with the Python "httpx" module.
    if IS_WINDOWS:
        src = os.path.join(bin_dir, "httpx.exe")
        dst = os.path.join(bin_dir, "httpx-toolkit.exe")
    else:
        src = os.path.join(bin_dir, "httpx")
        dst = os.path.join(bin_dir, "httpx-toolkit")
    if os.path.isfile(src) and not os.path.exists(dst):
        if DRY_RUN:
            log("would link httpx-toolkit -> httpx")
        else:
            try:
                if IS_WINDOWS:
                    shutil.copy2(src, dst)
                else:
                    os.symlink("httpx", dst)
                ok("linked httpx-toolkit -> httpx")
            except OSError as exc:
                warn("could not create %s (%s)" % (dst, exc))


def npm_global_bin() -> str:
    prefix = capture(["npm", "prefix", "-g"], as_user=True)
    if not prefix:
        return ""
    return prefix if IS_WINDOWS else os.path.join(prefix, "bin")


def ensure_python() -> None:
    if have("python3"):
        return
    if IS_MAC:
        brew_install(["python3"])
    elif IS_LINUX:
        linux_install(["python3", "pip"])
    elif IS_WINDOWS:
        windows_install(["python3"])
    augment_path()


def find_python(version: tuple) -> List[str]:
    """Return a Python command list whose interpreter is >= version."""
    if sys.version_info[:2] >= version:
        return [sys.executable]
    probe = ("import sys; raise SystemExit(0 if sys.version_info[:2] >= (%d, %d) else 1)"
             % version)
    candidates = [["python%d.%d" % version]]
    if IS_WINDOWS:
        candidates += [["py", "-%d.%d" % version], ["python"]]
    else:
        candidates.append(["python3"])
    for base in candidates:
        if not have(base[0]):
            continue
        try:
            proc = subprocess.run(
                _windows_resolve(base + ["-c", probe]),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except OSError:
            continue
        if proc.returncode == 0:
            return base
    return []


def install_pipx_tool(package: str, binary: str, force: bool,
                      min_python: Optional[tuple] = None) -> None:
    py = find_python(min_python) if min_python else []
    if min_python and not py:
        warn("%s needs Python %d.%d+; pipx will use its default interpreter"
             % ((package,) + tuple(min_python)))
    python_args = ["--python", py[0]] if py else []
    if have(binary) and not force:
        ok("%s already installed (--force upgrades it)" % binary)
        return
    ensure_python()
    if have("pipx"):
        if have(binary):
            rc = user_run(["pipx", "upgrade", package],
                          "pipx upgrade " + package, check=False)
            if rc == 0:
                return
            user_run(["pipx", "install", "--force"] + python_args + [package],
                     "pipx install --force " + package, check=False)
            return
        user_run(["pipx", "install"] + python_args + [package],
                 "pipx install " + package, check=False)
        return
    interpreter = py + ["-m", "pip"] if py else [sys.executable, "-m", "pip"]
    cmd = interpreter + ["install", "--user", "--upgrade", package]
    rc = user_run(cmd, "pip install --user --upgrade " + package, check=False)
    if rc != 0:
        # Debian/Ubuntu PEP 668 "externally managed environment"
        user_run(cmd + ["--break-system-packages"],
                 "pip install --user --break-system-packages " + package, check=False)


def install_node_tools(force: bool, skip_browsers: bool) -> None:
    if not have("npm"):
        warn("npm is not available; skipping endpoint-finder")
        return
    bin_dir = npm_global_bin()
    if bin_dir and os.path.isdir(bin_dir):
        prepend_path(bin_dir)
    if have("endpoint-finder") and not force:
        ok("endpoint-finder already installed")
    else:
        user_run(["npm", "install", "-g", "endpoint-finder"],
                 "npm install -g endpoint-finder", check=False)
    if bin_dir:
        prepend_path(bin_dir)
    if skip_browsers:
        warn("skipping Playwright Chromium download (--skip-browsers)")
        return
    user_run(["npx", "--yes", "playwright", "install", "chromium"],
             "install Playwright Chromium (Node)", check=False)


def install_techdetect(force: bool, skip_browsers: bool) -> None:
    if have("techdetect") and not force:
        ok("techdetect already installed")
        return
    if DRY_RUN:
        log("would install techdetect from " + TECHDETECT_REPO)
        return
    if not have("git"):
        warn("git is required to install techdetect")
        return
    tmpdir = tempfile.mkdtemp(prefix="boomer-techdetect-")
    try:
        user_run(["git", "clone", "--depth", "1", TECHDETECT_REPO, tmpdir],
                 "clone techdetect", check=False)
        installer = os.path.join(tmpdir, "install.py")
        if not os.path.isfile(installer):
            warn("techdetect install.py not found; see " + TECHDETECT_REPO)
            return
        args = [sys.executable, installer]
        if skip_browsers:
            args.append("--no-browser")
        user_run(args, "run techdetect installer", check=False, cwd=tmpdir)
    finally:
        if not DRY_RUN:
            shutil.rmtree(tmpdir, ignore_errors=True)


# --------------------------------------------------------------------------
# boomer itself
# --------------------------------------------------------------------------
def default_bin_dir() -> str:
    if IS_WINDOWS:
        return os.path.join(USER_HOME, ".local", "bin")
    if IS_MAC:
        for directory in ("/opt/homebrew/bin", "/usr/local/bin"):
            if os.path.isdir(directory) and os.access(directory, os.W_OK):
                return directory
        return os.path.join(USER_HOME, ".local", "bin")
    if os.path.isdir("/usr/local/bin") and os.access("/usr/local/bin", os.W_OK):
        return "/usr/local/bin"
    return os.path.join(USER_HOME, ".local", "bin")


def install_boomer(prefix: Optional[str], force: bool) -> None:
    source = os.path.join(SCRIPT_DIR, "boomer")
    if not os.path.isfile(source):
        warn("boomer script not found next to setup.py; skipping")
        return
    destination_dir = prefix or default_bin_dir()
    destination = os.path.join(destination_dir, "boomer")
    if DRY_RUN:
        log("would install boomer -> " + destination)
        return
    os.makedirs(destination_dir, exist_ok=True)
    if os.path.exists(destination) and not force:
        try:
            if open(destination, "rb").read() == open(source, "rb").read():
                ok("boomer already installed at " + destination)
                prepend_path(destination_dir)
                return
        except OSError:
            pass
        backup = destination + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
        try:
            shutil.copy2(destination, backup)
            info("backed up existing boomer to " + backup)
        except OSError:
            pass
    try:
        shutil.copy2(source, destination)
        os.chmod(destination, 0o755)
        ok("installed boomer -> " + destination)
    except OSError as exc:
        fail("could not install boomer to %s (%s)" % (destination, exc))
        return
    prepend_path(destination_dir)
    if IS_WINDOWS:
        info("run boomer from Git Bash or WSL (it is a bash script)")
    if IS_ROOT and SUDO_USER and SUDO_USER != "root":
        import pwd
        try:
            entry = pwd.getpwnam(SUDO_USER)
            os.chown(destination, entry.pw_uid, entry.pw_gid)
        except (KeyError, OSError):
            pass


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------
def check(verbose: bool = True) -> int:
    missing = 0
    if verbose:
        print("")
        print("  %-18s %-8s %s" % ("TOOL", "STATUS", "PATH"))
        print("  " + "-" * 66)
    for binary, label in REQUIRED_BINS:
        path = which(binary)
        if path:
            if verbose:
                print("  %-18s %-8s %s" % (binary, "ok", path))
        else:
            missing += 1
            if verbose:
                print("  %-18s %-8s %s" % (binary, "MISSING", label))
    boomer_path = which("boomer")
    if verbose:
        print("  %-18s %-8s %s" % ("boomer", "ok" if boomer_path else "MISSING",
                                   boomer_path or "not on PATH"))
    if missing:
        warn("%d required tool(s) missing" % missing)
    else:
        ok("all required tools present")
    return 0 if not missing and boomer_path else 1


def version_report() -> None:
    """Best-effort versions for the summary (never fails the setup)."""
    checks = [
        (["bash", "--version"], "bash"),
        (["curl", "--version"], "curl"),
        (["jq", "--version"], "jq"),
        (["go", "version"], "go"),
        (["node", "--version"], "node"),
        (["npm", "--version"], "npm"),
        (["httpx-toolkit", "-version"], "httpx-toolkit"),
        (["subfinder", "-version"], "subfinder"),
        (["techdetect", "--version"], "techdetect"),
    ]
    print("")
    for cmd, label in checks:
        if not have(cmd[0]):
            continue
        out = capture(cmd)
        if out:
            first = out.splitlines()[0].strip()
            print("  %-16s %s" % (label, first[:80]))


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def do_setup(force: bool, skip_browsers: bool, prefix: Optional[str]) -> int:
    info("boomer setup on %s (%s)" % (platform.system(), platform.machine()))
    if IS_ROOT and SUDO_USER and SUDO_USER != "root":
        info("running as root; user-level installs run as '%s'" % SUDO_USER)
    elif IS_ROOT and not IS_WINDOWS:
        warn("running as root without sudo; npm/pip/go installs will be root-owned")

    log("step 1/7: base tools (bash, curl, git, jq, Go, Node, Python)")
    ensure_base_tools(force=force)

    log("step 2/7: Go scanners (anew, subfinder, assetfinder, httpx)")
    install_go_tools(force=force)

    log("step 3/7: subdominator")
    install_pipx_tool("subdominator", "subdominator", force=force,
                      min_python=SUBDOMINATOR_PYTHON)

    log("step 4/7: endpoint-finder + Playwright Chromium")
    install_node_tools(force=force, skip_browsers=skip_browsers)

    log("step 5/7: techdetect + Playwright Chromium")
    install_techdetect(force=force, skip_browsers=skip_browsers)

    log("step 6/7: install boomer")
    install_boomer(prefix=prefix, force=force)

    log("step 7/7: persist PATH + verify")
    dirs = [d for d in (go_bin_dir(), npm_global_bin(),
                        os.path.join(USER_HOME, ".local", "bin"),
                        os.path.join(USER_HOME, "go", "bin")) if d]
    if not IS_WINDOWS:
        dirs.append(default_bin_dir())
    persist_path(dirs)
    augment_path()

    rc = check(verbose=True)
    version_report()

    print("")
    if rc == 0:
        ok("boomer is ready")
    else:
        warn("setup finished with missing tools (see above)")
    print("")
    print("  Next steps:")
    print("    1. Save API keys once (optional but recommended):")
    print("         boomer -g <VirusTotal-key>")
    print("         boomer -g st:<SecurityTrails-key>")
    print("         boomer -g otx:<AlienVault-OTX-key>")
    print("    2. Open a new terminal (or re-source your shell rc) so PATH changes apply.")
    print("    3. Try:")
    print("         boomer -a example.com")
    print("         boomer -c example.com-subdomains/subs.txt")
    if IS_WINDOWS:
        print("    4. Windows: run boomer inside Git Bash or WSL.")
    print("")
    return rc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="setup.py",
        description="Install every dependency boomer needs on Windows, macOS and Linux.",
        epilog="Links: %s  |  %s" % (ENDPOINT_FINDER_REPO, TECHDETECT_REPO),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--setup", action="store_true",
                        help="run the full end-to-end install")
    parser.add_argument("--check", action="store_true",
                        help="report installed tools and exit (no changes)")
    parser.add_argument("--force", action="store_true",
                        help="reinstall/upgrade tools even when already on PATH")
    parser.add_argument("--skip-browsers", action="store_true",
                        help="do not download Playwright Chromium")
    parser.add_argument("--prefix", metavar="DIR",
                        help="install the boomer script into DIR")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the actions without executing them")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="echo every command before running it")
    parser.add_argument("--version", action="version", version="boomer-setup 1.0")
    return parser


def main(argv: Sequence[str]) -> int:
    global DRY_RUN, VERBOSE
    parser = build_parser()
    args = parser.parse_args(argv)
    DRY_RUN = args.dry_run
    VERBOSE = args.verbose

    if sys.version_info < MIN_PYTHON:
        fail("Python %d.%d+ required (found %s)" % (MIN_PYTHON + (platform.python_version(),)))
        return 2

    if args.check and not args.setup:
        # still make user-installed tools visible before reporting
        if IS_ROOT and SUDO_USER:
            augment_path()
        return check(verbose=True)

    if not args.setup:
        parser.print_help()
        return 0

    if DRY_RUN:
        warn("dry run: no changes will be made")

    if IS_ROOT and SUDO_USER and SUDO_USER != "root":
        augment_path()
    else:
        augment_path()

    return do_setup(force=args.force, skip_browsers=args.skip_browsers,
                    prefix=args.prefix)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        fail("interrupted")
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as exc:  # keep the traceback out of the user's face
        fail("setup failed: %s" % exc)
        sys.exit(1)
