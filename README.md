# boomer

Fast subdomain enumeration in pure bash. No dead wrappers, no pasted keys.

## Install

```sh
chmod +x boomer
cp boomer /opt/homebrew/bin/boomer   # or /usr/local/bin, ~/go/bin
```

Save your keys once (reused automatically):

```sh
boomer -s <VirusTotal-key>
boomer -s st:<SecurityTrails-key>
```

Keys live in `~/.config/boomer/` with strict perms. Env overrides: `BOOMER_VT_API_KEY`, `BOOMER_SECURITYTRAILS_KEY`.

## Usage

```sh
boomer -a target.com     # subdomains from 10+ passive sources
boomer -b <url|file> [extra endpoint-finder args...]  # endpoint discovery
boomer -c|-d <file>      # sort live hosts by status code
boomer -e <httpx-file>   # split httpx output per status code
boomer -f <httpx-file>   # same, URL only
boomer -g <domain>       # AlienVault OTX urls
boomer -h <domain|file>  # VirusTotal undetected urls
boomer -i <url|file>     # tech detection
```

Empty sources leave no files behind and are skipped in the final `subs.txt`.

## Sources

crt.name, subdomain.center, urlscan, myssl, rapiddns, certspotter, netlas, hackertarget, shodan.io scrape, subfinder, assetfinder, subdominator, VirusTotal.

## Requirements

bash, curl, jq, anew. Optional per flag: subfinder, assetfinder, subdominator, httpx-toolkit, endpoint-finder, techdetect.
