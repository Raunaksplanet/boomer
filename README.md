# boomer

Fast subdomain enumeration and recon in pure bash — passive sources, endpoint
discovery, tech detection and status-code sorting, with no pasted API keys.

## Requirements

`boomer` is a bash wrapper: a few commands are required for every feature, and
the two headless scanners (`-b`, `-i`) are standalone projects that must be
installed separately.

| Tool | Needed by | Required? |
|---|---|---|
| `bash` 3.2+ | everything (the script itself) | **yes** |
| `curl` | `-a -g -h` and the installers | **yes** |
| `git` | `setup.py`, techdetect install | **yes** for setup |
| `jq` | `-a -g -h` | **yes** for those flags |
| `go` (toolchain) | installs `anew`, `subfinder`, `assetfinder`, `httpx` | **yes** for setup |
| `node` + `npm` 18+ | `-b` via [endpoint-finder](https://github.com/Raunaksplanet/endpoint-finder) | **yes** for `-b` |
| `python3` 3.9+ | `-i` via [techdetect](https://github.com/Raunaksplanet/techdetect) | **yes** for `-i` |
| `anew` | `-a -c -d` | **yes** for those flags |
| `subfinder` | `-a` (optional source) | optional |
| `assetfinder` | `-a` (optional source) | optional |
| `subdominator` | `-a` (optional source) | optional |
| `httpx-toolkit` | `-c -d -f` | **yes** for those flags |
| `endpoint-finder` | `-b` | **yes** for `-b` |
| `techdetect` | `-i` | **yes** for `-i` |

### Per-flag matrix

| Flag | Feature | External binaries | API key |
|---|---|---|---|
| `-a` | AllDomz (subdomains) | `curl`, `anew`; `jq` for 6 sources; optional `subfinder`, `assetfinder`, `subdominator` | optional VT + SecurityTrails |
| `-b` | EndpointFinder | `endpoint-finder` → Node + Playwright Chromium | — |
| `-c` | Domains → status files | `httpx-toolkit`, `anew` | — |
| `-d` | Domains → status files (simple) | `httpx-toolkit`, `anew` | — |
| `-e` | Split httpx output locally | none | — |
| `-f` | httpx probe + split | `httpx-toolkit` | — |
| `-g` | AlienVault OTX URLs | `curl`, `jq` | optional OTX |
| `-h` | VirusTotal undetected URLs | `curl`, `jq` | **required** VT |
| `-i` | TechDetect | `techdetect` → Python + Playwright Chromium | — |
| `-s` | Save API key | none | — |

### Headless scanners (separate projects)

`-b` and `-i` delegate to two standalone tools:

- **[Raunaksplanet/endpoint-finder](https://github.com/Raunaksplanet/endpoint-finder)** — Node.js 18+, `playwright@1.59.0` and a Chromium build.
  ```bash
  npm install -g endpoint-finder
  npx playwright install chromium
  ```
- **[Raunaksplanet/techdetect](https://github.com/Raunaksplanet/techdetect)** — Python 3.9+, `playwright` + `httpx`, and a Chromium build.
  ```bash
  git clone https://github.com/Raunaksplanet/techdetect
  cd techdetect && python3 install.py
  ```

Both need a real Chromium download (`python -m playwright install chromium` /
`npx playwright install chromium`); a bare `pip install playwright` is not
enough. If Chromium is missing, `-b`/`-i` fail at launch.

## One-command setup

`setup.py` installs **everything above** end-to-end on Windows, macOS and
Linux: base tools, Go scanners, `httpx-toolkit`, `subdominator`,
`endpoint-finder` + Chromium, `techdetect` + Chromium, and `boomer` itself on
PATH.

```bash
sudo python3 setup.py --setup     # macOS / Linux (recommended)
python  setup.py --setup          # Windows (no sudo needed)
```

Helpful flags:

```bash
python3 setup.py --help           # show every option
python3 setup.py --check          # report what is installed, change nothing
sudo python3 setup.py --setup --force          # reinstall everything
sudo python3 setup.py --setup --skip-browsers  # skip Chromium downloads
sudo python3 setup.py --setup --prefix ~/.local/bin
sudo python3 setup.py --setup --dry-run -v     # show commands, do nothing
```

`setup.py` is idempotent — tools already on PATH are left alone — and it drops
privileges to `$SUDO_USER` for Homebrew/npm/pip/Go so nothing is written as
root-owned. When run without `sudo`, system packages use `sudo` as needed.

Per-OS notes:

| OS | Command | Notes |
|---|---|---|
| macOS | `sudo python3 setup.py --setup` | Uses Homebrew (installs it if missing). |
| Linux | `sudo python3 setup.py --setup` | Uses apt / dnf / yum / pacman / zypper / apk. |
| Windows | `python setup.py --setup` | Uses winget (choco as fallback). Run `boomer` from **Git Bash** or **WSL** — it is a bash script. |

After setup, open a new terminal (or re-source your shell rc) so the PATH
changes apply, then verify:

```bash
boomer --help
python3 setup.py --check
```

## Manual setup

If you prefer to install things yourself:

```bash
# base (macOS)
brew install jq anew go node
go install github.com/tomnomnom/anew@latest
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/tomnomnom/assetfinder@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
ln -sf "$(go env GOPATH)/bin/httpx" "$(go env GOPATH)/bin/httpx-toolkit"

# subdominator (Python)
pipx install subdominator        # or: pip install --user subdominator

# headless scanners
npm install -g endpoint-finder && npx playwright install chromium
git clone https://github.com/Raunaksplanet/techdetect && (cd techdetect && python3 install.py)

# boomer
chmod +x boomer
cp boomer /opt/homebrew/bin/boomer   # or /usr/local/bin / ~/.local/bin
```

> **Why `httpx-toolkit`?** boomer calls ProjectDiscovery's `httpx` by that name
> so it never collides with the Python `httpx` module. `setup.py` creates the
> alias automatically.

## API keys

All keys are optional except VirusTotal for `-h`. Save once; keys are reused.

```bash
boomer -s <VirusTotal-key>
boomer -s st:<SecurityTrails-key>
boomer -s otx:<AlienVault-OTX-key>
```

Keys live in `~/.config/boomer/` with `700` directory / `600` file
permissions. Environment overrides: `BOOMER_VT_API_KEY`,
`BOOMER_SECURITYTRAILS_KEY`, `BOOMER_OTX_API_KEY`.

> The public source ships **no** built-in keys. If you previously ran a build
> with embedded keys, rotate them.

Rate limits are tunable: `BOOMER_VT_DELAY`, `BOOMER_VT_BACKOFF`,
`BOOMER_VT_RETRIES`, `BOOMER_OTX_DELAY`, `BOOMER_OTX_BACKOFF`.

## Usage

```bash
boomer -a target.com                    # subdomains from 10+ passive sources
boomer -b <url|file> [args...]          # endpoint discovery
boomer -c <file>                        # live hosts → 200s/300s/400s/500s.txt
boomer -d <file>                        # same, bare URLs only
boomer -e <httpx-file>                  # split existing httpx output by status
boomer -f <file>                        # probe hosts, then split by status
boomer -g <domain|file>                 # AlienVault OTX URLs
boomer -h <domain|file>                 # VirusTotal undetected URLs
boomer -i <url|file> [args...]          # tech detection
boomer -s <key>                         # save an API key
```

Extra arguments after `-b`/`-i` are forwarded verbatim to the delegate:

```bash
boomer -b https://example.com --scope host --wait 3
boomer -i example.com --workers 1 --delay 2
```

`-a` writes `SubList1..7.txt` (non-empty sources only) and merges them into
`subs.txt`. `-g` appends to `AlienResult.txt`; `-h` appends to
`VirusTotalResult.txt`.

## Sources (`-a`)

crt.name, subdomain.center, urlscan.io, myssl, certspotter, netlas,
SecurityTrails, hackertarget, rapiddns, shodan.io scrape, subfinder,
assetfinder, subdominator, VirusTotal.

Empty sources leave no files behind and are skipped in the final `subs.txt`.

## Notes

- **Windows:** run boomer under Git Bash or WSL. `setup.py` installs the Windows
  toolchain via winget and puts `boomer` in `%USERPROFILE%\.local\bin`.
- **PATH:** `setup.py` appends `~/.local/bin`, `$(go env GOPATH)/bin` and npm's
  global bin directory to your shell profile (or the user PATH on Windows).
- **Fail-fast vs graceful:** only `-b` and `-i` hard-fail when their delegate
  is missing. `-a` warns and skips unavailable optional sources; `-g` runs
  keyless at a slower rate.
- **Authorized targets only.** You are responsible for staying in scope of
  whatever program you are testing.

## Links

- boomer — https://github.com/Raunaksplanet/boomer
- endpoint-finder — https://github.com/Raunaksplanet/endpoint-finder
- techdetect — https://github.com/Raunaksplanet/techdetect
