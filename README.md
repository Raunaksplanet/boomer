# boomer

Subdomain enumeration and recon in pure bash: passive subdomain sources,
endpoint discovery, tech detection, status-code sorting and screenshots.

## Contents

| Section | What you'll find |
|---|---|
| [Quick start](#quick-start) | Clone, install, run |
| [Installation](#installation) | Automated setup, manual setup, Windows |
| [Tools required](#tools-required) | What each flag needs |
| [Usage](#usage) | Flags, examples, per-command help |
| [API keys](#api-keys) | Save keys once, reuse them |
| [Output](#output) | Folder layouts for `-a` and `-c` |
| [Updating](#updating) | Upgrade boomer's tools |
| [Notes](#notes) | Troubleshooting and scope |

## Quick start

```bash
git clone https://github.com/Raunaksplanet/boomer
cd boomer
sudo python3 setup.py --setup     # macOS / Linux
boomer -h
```

Windows: run `python setup.py --setup` (no `sudo`) and use **Git Bash** or **WSL**.

## Installation

`setup.py` installs everything: base tools, the Go scanners, `httpx-toolkit`,
`subdominator`, the headless tools plus Chromium, and `boomer` itself on
PATH. It is safe to re-run; existing tools are left alone unless you pass
`--force`.

| Command | What it does |
|---|---|
| `sudo python3 setup.py --setup` | Install or repair everything (macOS / Linux) |
| `python setup.py --setup` | Same, on Windows |
| `python3 setup.py --check` | Report what is installed, change nothing |
| `sudo python3 setup.py --setup --force` | Upgrade everything in place |
| `sudo python3 setup.py --setup --skip-browsers` | Skip the Chromium downloads |
| `sudo python3 setup.py --setup --prefix ~/.local/bin` | Choose where `boomer` goes |
| `python3 setup.py --setup --dry-run -v` | Show commands without running them |

Open a new terminal afterwards so PATH changes apply, then run `boomer -h`.

<details>
<summary><strong>Manual setup</strong></summary>

```bash
# base (macOS)
brew install jq anew go node

# Go scanners
go install github.com/tomnomnom/anew@latest
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/tomnomnom/assetfinder@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
ln -sf "$(go env GOPATH)/bin/httpx" "$(go env GOPATH)/bin/httpx-toolkit"

# subdominator (needs Python 3.13+)
pipx install --python python3.13 subdominator

# headless tools
npm install -g endpoint-finder && npx playwright install chromium
git clone https://github.com/Raunaksplanet/techdetect
(cd techdetect && python3 install.py)
git clone https://github.com/Raunaksplanet/websnap
(cd websnap && ./install.sh)

# boomer
chmod +x boomer
cp boomer /opt/homebrew/bin/boomer   # or /usr/local/bin, ~/.local/bin
```

> **Why `httpx-toolkit`?** boomer calls ProjectDiscovery's `httpx` by that name
> so it never collides with the Python `httpx` module. `setup.py` creates the
> alias automatically.

</details>

## Tools required

| Tool | Used by | Notes |
|---|---|---|
| `bash` 3.2+ | everything | The script itself |
| `curl`, `jq` | `-a`, `-d`, `-e` | Required for those flags |
| `anew` | `-a` | Merges and de-duplicates results |
| `httpx-toolkit` | `-c` | Only when probing (parsing needs nothing) |
| `subfinder`, `assetfinder`, `subdominator` | `-a` | Optional extra sources (subdominator needs Python 3.13+) |
| [endpoint-finder](https://github.com/Raunaksplanet/endpoint-finder) | `-b` | Node 18+ and Playwright Chromium |
| [techdetect](https://github.com/Raunaksplanet/techdetect) | `-f` | Python 3.9+ and Playwright Chromium |
| [websnap](https://github.com/Raunaksplanet/websnap) | `-g` | Node 18+ and Playwright Chromium; `setup.py` installs it |

A bare `pip install playwright` is not enough — both scanners need a real
Chromium download (`npx playwright install chromium`). `setup.py` does this for
you.

## Usage

| Flag | Feature | Example |
|---|---|---|
| `-a` | Subdomains from 14 passive sources | `boomer -a example.com` |
| `-b` | Endpoint discovery | `boomer -b https://example.com` |
| `-c` | Status-code sorting (probe or parse) | `boomer -c subs.txt` |
| `-d` | AlienVault OTX URLs | `boomer -d example.com` |
| `-e` | VirusTotal undetected URLs | `boomer -e example.com` |
| `-f` | Tech detection | `boomer -f example.com` |
| `-g` | Websnap full-page screenshots | `boomer -g subs.txt` |
| `--key` | Save an API key | `boomer --key <VirusTotal-key>` |
| `-h` | Top-level usage | `boomer -h` |

Arguments after `-b`, `-c`, `-f` and `-g` are passed straight to the underlying
tool:

```bash
boomer -b https://example.com --scope host --wait 3
boomer -c subs.txt --threads 100 --timeout 10
boomer -f example.com --workers 1 --delay 2
boomer -g subs.txt --threads 5
```

Every command has its own help page, e.g. `boomer -a -h`, `boomer -g -h`,
`boomer --key -h`.

`-a` accepts a domain, subdomain, URL or `*.` wildcard and reduces it to the
registrable domain first:

```bash
boomer -a https://www.dell.com/en-in   # -> dell.com
boomer -a foo.bar.example.co.uk        # -> example.co.uk
boomer -a 192.168.1.1                  # rejected: IP address
```

## API keys

Only `-e` (VirusTotal) needs a key; the others are optional. Save once and
boomer reuses them:

```bash
boomer --key <VirusTotal-key>
boomer --key st:<SecurityTrails-key>
boomer --key otx:<AlienVault-OTX-key>
```

Keys live in `~/.config/boomer/` (700 directory, 600 files). Environment
overrides: `BOOMER_VT_API_KEY`, `BOOMER_SECURITYTRAILS_KEY`,
`BOOMER_OTX_API_KEY`. No keys are built into the source.

## Output

`-a` writes one folder per target; empty sources leave no file:

```text
dell.com-subdomains/
├── SubList1.txt … SubList7.txt   # one file per source
└── subs.txt                     # merged, de-duplicated
```

`-c` writes one file pair per status code, sorted and de-duplicated:

```text
example.com-statuscodes/
├── clean-200.txt   # bare URLs
├── clean-301.txt
├── full-200.txt    # full httpx lines
└── full-301.txt
```

`-g` writes full-page screenshots into `<base>-screenshots/`, using the same
base name as `-a` and `-c`:

```text
dell.com-screenshots/
├── www.dell.com.png
└── shop.dell.com.png
```

Only images are kept. `websnap` handles popups, lazy loading and blank-page
retries; extra arguments go straight to it (`-c`, `--per-apex`, `--settle`).
For a crawled URL list the path is kept in the name:
`zerodha.com-open-account-huf.png`; query strings get a short hash suffix.

`-d` appends to `AlienResult.txt`; `-e` appends to `VirusTotalResult.txt`.
Folders contain result data only — no metadata files.

### `-c` options

| Option | Effect |
|---|---|
| `--probe` / `--no-probe` | Force probing or force parsing |
| `--clean-only` / `--full-only` | Only bare URLs / only full lines |
| `--include-failed` | Bucket status-less lines as `000` |
| `--tech` | Add `-td` to the httpx probe |
| `--append` | Merge into existing files instead of overwriting |
| `--outdir DIR` | Override `<base>-statuscodes/` |
| `--threads N` `--timeout N` `--retries N` `--rate-limit N` | httpx tuning |

## Updating

```bash
sudo python3 setup.py --setup --force
```

<details>
<summary><strong>Update tools individually</strong></summary>

```bash
go install github.com/tomnomnom/anew@latest
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/tomnomnom/assetfinder@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
pipx upgrade subdominator            # Python 3.13+
npm install -g endpoint-finder@latest && npx playwright install chromium
git -C techdetect pull && (cd techdetect && python3 install.py)
git -C websnap pull && (cd websnap && ./install.sh)
```

If `pipx upgrade subdominator` fails, reinstall it:
`pipx install --force --python python3.13 subdominator`.

</details>

## Notes

- **PATH:** `setup.py` adds `~/.local/bin`, the Go bin directory and npm's
  global bin to your shell profile.
- **Missing tools:** only `-b` and `-f` hard-fail. `-a` warns and skips
  unavailable sources; `-d` runs keyless at a slower rate.
- **Authorized targets only.** Stay in scope of whatever program you test.

## Links

- [boomer](https://github.com/Raunaksplanet/boomer)
- [endpoint-finder](https://github.com/Raunaksplanet/endpoint-finder)
- [techdetect](https://github.com/Raunaksplanet/techdetect)
- [websnap](https://github.com/Raunaksplanet/websnap)
