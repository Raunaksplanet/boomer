#!/bin/bash

BOOMER_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/boomer"
BOOMER_VT_KEY_FILE="$BOOMER_CONFIG_DIR/vt_api_key"
BOOMER_ST_KEY_FILE="$BOOMER_CONFIG_DIR/securitytrails_key"

boomer_config_dir() {
    mkdir -p "$BOOMER_CONFIG_DIR" 2>/dev/null && chmod 700 "$BOOMER_CONFIG_DIR" 2>/dev/null
}

boomer_vt_key() {
    if [[ -n "${BOOMER_VT_API_KEY:-}" ]]; then
        echo "$BOOMER_VT_API_KEY"
        return 0
    fi
    if [[ -f "$BOOMER_VT_KEY_FILE" ]]; then
        tr -d ' \t\r\n' < "$BOOMER_VT_KEY_FILE"
    fi
    return 0
}

boomer_st_key() {
    if [[ -n "${BOOMER_SECURITYTRAILS_KEY:-}" ]]; then
        echo "$BOOMER_SECURITYTRAILS_KEY"
        return 0
    fi
    if [[ -f "$BOOMER_ST_KEY_FILE" ]]; then
        tr -d ' \t\r\n' < "$BOOMER_ST_KEY_FILE"
    fi
    return 0
}

boomer_save_key() {
    local spec="$1"
    local target="$BOOMER_VT_KEY_FILE"
    local label="VirusTotal"
    if [[ "$spec" == st:* ]]; then
        target="$BOOMER_ST_KEY_FILE"
        label="SecurityTrails"
        spec="${spec#st:}"
    fi
    spec="$(echo "$spec" | tr -d ' \t\r\n')"
    if [[ -z "$spec" ]]; then
        echo "Usage: $0 -s <VirusTotal-API-key>  (or  $0 -s st:<SecurityTrails-key>)" >&2
        return 1
    fi
    boomer_config_dir
    printf '%s' "$spec" > "$target"
    chmod 600 "$target"
    echo "[INFO] $label API key saved to $target (reused automatically)"
}

usage() {
    echo "Usage: $0 [options]
    -a        AllDomz
    -b        AllUrls
    -c        Domains to status codes
    -d        Domains to status codes [Simple]
    -e        HTTPX To Specific Status Code Text File
    -f        HTTPX To Specific Status Code Text File [Simple]
    -g        Alien Url's
    -h        Virus Total
    -i        TechDetect
    -s        Save API key permanently (-s <VT-key> or -s st:<SecurityTrails-key>)"
    exit 1
}

httpx_status_code() {
    local input_file="$1"
    if [[ ! -f "$input_file" ]]; then
        echo "[ERROR] file not found: $input_file" >&2
        return 1
    fi
    local status_codes=($(grep -oE '\[[0-9]{3}\]' "$input_file" | sort -u | tr -d '[]'))

    for code in "${status_codes[@]}"; do
        grep -F "[$code]" "$input_file" > "${code}.txt"
    done

    echo "Extraction completed."
}

httpx_status_code_simple() {
    local input_file="$1"
    if [[ ! -f "$input_file" ]]; then
        echo "[ERROR] file not found: $input_file" >&2
        return 1
    fi
    if ! command -v httpx-toolkit >/dev/null 2>&1; then
        echo "[ERROR] httpx-toolkit not found on PATH" >&2
        return 1
    fi
    cat "$input_file" | httpx-toolkit -td -sc -nc -silent -title | awk '{print $1, $2}' | while read url status; do
        status_code=$(echo "$status" | tr -d '[]')
        echo "$url" >> "${status_code}.txt"
    done
    echo "URLs sorted by status codes."
}

AlienUrl() {
    local domain=$1
    if [[ -z "$domain" ]]; then
        echo "Usage: $0 -g <domain>" >&2
        return 1
    fi
    if ! command -v jq >/dev/null 2>&1; then
        echo "[ERROR] jq not found on PATH" >&2
        return 1
    fi
    local output_file="AlienResult.txt"
    local base_url="https://otx.alienvault.com/api/v1/indicators/domain/$domain/url_list?limit=500&page="
    local page=1
    local max_pages=20

    echo "[INFO] Scraping URLs for domain: $domain"

    while (( page <= max_pages )); do
        if ! response=$(curl -s --max-time 60 "$base_url$page"); then
            echo "[ERROR] request failed for page $page" >&2
            break
        fi
        urls=$(echo "$response" | jq -r '.url_list[].url' 2>/dev/null)

        if [ -z "$urls" ]; then
            echo "[INFO] No more URLs for $domain."
            break
        fi

        echo "$urls" >>"$output_file"
        page=$((page + 1))
    done

    if [ -s "$output_file" ]; then
        echo "[INFO] URLs saved to $output_file"
    else
        echo "[INFO] No URLs found for domain: $domain."
    fi
}

VirusTotal() {
    local input=$1
    local api_key

    if [[ -z "$input" ]]; then
        echo "Usage: $0 -h <domain|file>" >&2
        return 1
    fi
    if ! command -v jq >/dev/null 2>&1; then
        echo "[ERROR] jq not found on PATH" >&2
        return 1
    fi

    api_key="$(boomer_vt_key)"
    if [[ -z "$api_key" ]]; then
        if [[ -t 0 ]]; then
            read -r -s -p "Enter VirusTotal API key (saved permanently to $BOOMER_VT_KEY_FILE): " api_key
            echo
            if [[ -z "$api_key" ]]; then
                echo "[ERROR] no API key given" >&2
                return 1
            fi
            boomer_save_key "$api_key" || return 1
        else
            echo "[ERROR] no VirusTotal API key saved. Run once: $0 -s <APIKEY>" >&2
            return 1
        fi
    fi

    local targets=()
    local out=""
    if [[ -f "$input" ]]; then
        echo "[INFO] Detected file input: $input"
        local base="$(basename "$input")"
        base="${base%.*}"
        [[ -z "$base" ]] && base="targets"
        out="${base}-virustotal.txt"
        while IFS= read -r line || [[ -n "$line" ]]; do
            line="${line%$'\r'}"
            line="$(echo "$line" | xargs)"
            [[ -z "$line" || "$line" == \#* ]] && continue
            targets+=("$line")
        done < "$input"
    else
        echo "[INFO] Detected URL/host input: $input"
        local safe="$input"
        safe="${safe#https://}"
        safe="${safe#http://}"
        safe="${safe%%/*}"
        safe="${safe//[^A-Za-z0-9.-]/_}"
        [[ -z "$safe" ]] && safe="target"
        out="$safe-virustotal.txt"
        targets=("$input")
    fi
    if [[ ${#targets[@]} -eq 0 ]]; then
        echo "[ERROR] no valid targets" >&2
        return 1
    fi
    : > "$out"

    local domain URL response undetected_urls code
    for domain in "${targets[@]}"; do
        domain="${domain#https://}"
        domain="${domain#http://}"
        domain="${domain%%/*}"
        domain="${domain%%:*}"
        URL="https://www.virustotal.com/vtapi/v2/domain/report?apikey=$api_key&domain=$domain"

        echo -e "\nFetching data for domain: \033[1;34m$domain\033[0m (using saved API key)"
        echo "Domain: $domain" >> "$out"
        if ! response=$(curl -s --max-time 60 "$URL"); then
            echo -e "\033[1;31mError fetching data for domain: $domain\033[0m"
            echo "ERROR fetching data" >> "$out"
            echo "------------------------------------------" >> "$out"
            continue
        fi

        code=$(echo "$response" | jq -r '.response_code // empty' 2>/dev/null)
        if [[ "$code" == "0" ]]; then
            echo -e "\033[1;33mDomain not found in VirusTotal: $domain\033[0m"
            echo "Not found in VirusTotal" >> "$out"
        elif [[ "$code" == "-2" ]]; then
            echo -e "\033[1;33mAnalysis queued in VirusTotal: $domain\033[0m"
            echo "Analysis queued" >> "$out"
        else
            undetected_urls=$(echo "$response" | jq -r '.undetected_urls[][0]' 2>/dev/null)
            if [[ -z "$undetected_urls" ]]; then
                echo -e "\033[1;33mNo undetected URLs found for domain: $domain\033[0m"
                echo "No undetected URLs found" >> "$out"
            else
                echo -e "\033[1;32mUndetected URLs for domain: $domain\033[0m"
                echo "$undetected_urls"
                echo "Undetected URLs:" >> "$out"
                echo "$undetected_urls" >> "$out"
            fi
        fi
        echo "------------------------------------------" >> "$out"
    done
    echo "[INFO] Results saved to $out"
}

AllDomz() {
    local domain=$1
    if [[ -z "$domain" ]]; then
        echo "Usage: $0 -a <domain>" >&2
        return 1
    fi
    if ! command -v anew >/dev/null 2>&1; then
        echo "[ERROR] anew not found on PATH" >&2
        return 1
    fi
    local apex="$domain"
    apex="${apex#https://}"
    apex="${apex#http://}"
    apex="${apex%%/*}"
    apex="${apex%%:*}"
    apex="$(echo "$apex" | tr '[:upper:]' '[:lower:]' | xargs)"
    if [[ -z "$apex" ]]; then
        echo "[ERROR] could not parse domain from input: $domain" >&2
        return 1
    fi
    prune_empty() { [[ -f "$1" ]] && [[ ! -s "$1" ]] && rm -f "$1"; }
    if command -v curl >/dev/null 2>&1; then
        if ! curl -s --max-time 60 "https://crt.name/v1/search?apex=$apex" | grep -v -E '^(missing apex parameter|invalid apex)' | sed 's/^\*\.//' | anew SubList1.txt; then
            echo "[WARN] crt.name request failed for $apex, skipping" >&2
        fi
    else
        echo "[WARN] curl not found, skipping crt.name source" >&2
    fi
    prune_empty SubList1.txt
    if command -v curl >/dev/null 2>&1; then
        local sdom_tmp
        sdom_tmp="$(mktemp)"
        if command -v jq >/dev/null 2>&1; then
            curl -s --max-time 30 "https://api.subdomain.center/?domain=$apex" | jq -r '.[]?' 2>/dev/null >> "$sdom_tmp" &
            curl -s --max-time 30 "https://urlscan.io/api/v1/search/?q=domain:$apex" | jq -r '.results[].page.domain? // empty' 2>/dev/null >> "$sdom_tmp" &
            curl -s --max-time 30 "https://myssl.com/api/v1/discover_sub_domain?domain=$apex" | jq -r '.data[].domain? // empty' 2>/dev/null >> "$sdom_tmp" &
            curl -s --max-time 30 "https://api.certspotter.com/v1/issuances?domain=$apex&include_subdomains=true&expand=dns_names" | jq -r '.[].dns_names[]?' 2>/dev/null | sed 's/^\*\.//' >> "$sdom_tmp" &
            curl -s --max-time 30 "https://app.netlas.io/api/domains/?q=domain:*.$apex+AND+NOT+domain:$apex&source_type=include" | jq -r '.items[].data.domain? // empty' 2>/dev/null >> "$sdom_tmp" &
            st_key="$(boomer_st_key)"
            if [[ -n "$st_key" ]]; then
                curl -s --max-time 30 -X GET "https://api.securitytrails.com/v1/domain/$apex/subdomains" -H "Accept: application/json" -H "APIKEY: $st_key" | jq -r --arg d "$apex" '.subdomains[]? + "." + $d' 2>/dev/null >> "$sdom_tmp" &
            else
                echo "[WARN] no SecurityTrails key saved, skipping that source (run: $0 -s st:<KEY>)" >&2
            fi
        else
            echo "[WARN] jq not found, skipping jq-based subdom sources" >&2
        fi
        curl -s --max-time 30 "https://api.hackertarget.com/hostsearch/?q=$apex" | cut -d ',' -f1 | grep -iE "^[A-Za-z0-9_.-]+\.${apex//./\\.}$" >> "$sdom_tmp" &
        curl -s --max-time 30 -A "Mozilla/5.0" "https://rapiddns.io/subdomain/$apex?full=1" | grep -oE "[A-Za-z0-9._-]+\.$apex" 2>/dev/null >> "$sdom_tmp" &
        wait
        tr -d '\r' < "$sdom_tmp" | sed 's/^\*\.//;s/^[[:space:]]*//;s/[[:space:]]*$//' | grep -E '^[A-Za-z0-9_.-]+$' | grep -iv "^\*" | grep -iE "(^|\.)${apex//./\\.}$" | sort -u | anew SubList2.txt
        rm -f "$sdom_tmp"
    else
        echo "[WARN] curl not found, skipping subdom sources" >&2
    fi
    prune_empty SubList2.txt
    if command -v curl >/dev/null 2>&1; then
        if ! curl -s --max-time 30 -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36" -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" -H "Referer: https://account.shodan.io/?language=en" "https://www.shodan.io/domain/$apex" | sed -n '/<ul id="subdomains">/,/<\/ul>/p' | grep -oE '<li>[^<]+</li>' | sed -E 's/<\/?li>//g;s/^[[:space:]]*//;s/[[:space:]]*$//' | while IFS= read -r prefix; do
            [[ -z "$prefix" ]] && continue
            if [[ "$prefix" == "$apex" || "$prefix" == *".$apex" ]]; then
                echo "$prefix"
            else
                echo "$prefix.$apex"
            fi
        done | anew SubList3.txt; then
            echo "[WARN] shodan.io scrape failed for $apex, skipping" >&2
        fi
    else
        echo "[WARN] curl not found, skipping shodan.io source" >&2
    fi
    prune_empty SubList3.txt
    if command -v subfinder >/dev/null 2>&1; then
        subfinder -all -recursive -silent -nc -d "$domain" | anew SubList4.txt
    else
        echo "[WARN] subfinder not found, skipping" >&2
    fi
    prune_empty SubList4.txt
    if command -v assetfinder >/dev/null 2>&1; then
        assetfinder -subs-only "$domain" | anew SubList5.txt
    else
        echo "[WARN] assetfinder not found, skipping" >&2
    fi
    prune_empty SubList5.txt
    if command -v subdominator >/dev/null 2>&1; then
        subdominator -nc -d "$domain" | anew SubList6.txt
    else
        echo "[WARN] subdominator not found, skipping" >&2
    fi
    prune_empty SubList6.txt
    if command -v curl >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
        vt_sub_key="$(boomer_vt_key)"
        if [[ -n "$vt_sub_key" ]]; then
            curl -s --max-time 60 "https://www.virustotal.com/vtapi/v2/domain/report?apikey=$vt_sub_key&domain=$domain" | jq -r '.subdomains[]?, .domain_siblings[]?' 2>/dev/null | anew SubList7.txt
        else
            echo "[WARN] no VirusTotal API key saved, skipping that source (run: $0 -s <APIKEY>)" >&2
        fi
    else
        echo "[WARN] curl/jq not found, skipping VirusTotal source" >&2
    fi
    prune_empty SubList7.txt
    local parts=()
    local f
    for f in SubList1.txt SubList2.txt SubList3.txt SubList4.txt SubList5.txt SubList6.txt SubList7.txt; do
        [[ -s "$f" ]] && parts+=("$f")
    done
    if [[ ${#parts[@]} -eq 0 ]]; then
        echo "[ERROR] no subdomain data collected" >&2
        return 1
    fi
    cat "${parts[@]}" | anew subs.txt
    prune_empty subs.txt
}

EndpointFinder() {
    local input="$1"
    shift || true
    local finder=""

    if [[ -z "$input" ]]; then
        echo "Usage: $0 -b <url|file> [extra endpoint-finder args...]"
        echo "Example: $0 -b https://example.com"
        echo "Example: $0 -b subs.txt"
        return 1
    fi

    if command -v endpoint-finder >/dev/null 2>&1; then
        finder="endpoint-finder"
    else
        echo "[ERROR] endpoint-finder not found on PATH" >&2
        return 1
    fi

    if [[ -f "$input" ]]; then
        echo "[INFO] Detected file input: $input"
        "$finder" -i "$input" "$@"
    else
        echo "[INFO] Detected URL/host input: $input"
        "$finder" -u "$input" "$@"
    fi
}

CleanDomains() {
    local domain=$1
    if [[ ! -f "$domain" ]]; then
        echo "[ERROR] file not found: $domain" >&2
        return 1
    fi
    if ! command -v httpx-toolkit >/dev/null 2>&1; then
        echo "[ERROR] httpx-toolkit not found on PATH" >&2
        return 1
    fi
    if ! command -v anew >/dev/null 2>&1; then
        echo "[ERROR] anew not found on PATH" >&2
        return 1
    fi
    cat "$domain" | httpx-toolkit -td -sc -nc -silent -title | tee >(grep "\[3[0-9][0-9]\]" | anew 300s.txt) >(grep "\[4[0-9][0-9]\]" | anew 400s.txt) >(grep "\[5[0-9][0-9]\]" | anew 500s.txt) | grep "\[2[0-9][0-9]\]" | anew 200s.txt
}

CleanDomains_Simple() {
    local input_file="$1"
    if [[ ! -f "$input_file" ]]; then
        echo "[ERROR] file not found: $input_file" >&2
        return 1
    fi
    if ! command -v httpx-toolkit >/dev/null 2>&1; then
        echo "[ERROR] httpx-toolkit not found on PATH" >&2
        return 1
    fi
    if ! command -v anew >/dev/null 2>&1; then
        echo "[ERROR] anew not found on PATH" >&2
        return 1
    fi
    cat "$input_file" | httpx-toolkit -td -sc -nc -silent -title | awk '{print $1, $2}' | tee \
        >(grep "\[3[0-9][0-9]\]" | awk '{print $1}' | anew 300s.txt) \
        >(grep "\[4[0-9][0-9]\]" | awk '{print $1}' | anew 400s.txt) \
        >(grep "\[5[0-9][0-9]\]" | awk '{print $1}' | anew 500s.txt) \
        | grep "\[2[0-9][0-9]\]" | awk '{print $1}' | anew 200s.txt
    echo "URLs categorized by status codes."
}

TechDetect() {
    local input="$1"
    shift || true
    local detector=""
    local out=""

    if [[ -z "$input" ]]; then
        echo "Usage: $0 -i <url|file> [extra techdetect args...]" >&2
        return 1
    fi

    if command -v techdetect >/dev/null 2>&1; then
        detector="techdetect"
    else
        echo "[ERROR] techdetect not found on PATH" >&2
        return 1
    fi

    if [[ -f "$input" ]]; then
        echo "[INFO] Detected file input: $input"
        out="$(basename "$input")"
        out="${out%.*}-tech-detection.txt"
        [[ -z "$out" || "$out" == "-tech-detection.txt" ]] && out="tech-detection.txt"
        "$detector" -f "$input" -o "$out" "$@"
    else
        echo "[INFO] Detected URL/host input: $input"
        out="$input"
        out="${out#https://}"
        out="${out#http://}"
        out="${out%%/*}"
        out="${out//[^A-Za-z0-9.-]/_}"
        [[ -z "$out" ]] && out="target"
        out="$out-tech-detection.txt"
        "$detector" "$input" -o "$out" "$@"
    fi
}

main() {
    while getopts ":a:b:c:d:e:f:g:h:i:s:" opt; do
        case $opt in
            a) AllDomz "$OPTARG" ;;
            b) EndpointFinder "$OPTARG" ;;
            c) CleanDomains "$OPTARG" ;;
            d) CleanDomains_Simple "$OPTARG" ;;
            e) httpx_status_code "$OPTARG" ;;
            f) httpx_status_code_simple "$OPTARG" ;;
            g) AlienUrl "$OPTARG" ;;
            h) VirusTotal "$OPTARG" ;;
            i) TechDetect "$OPTARG" ;;
            s) boomer_save_key "$OPTARG" ;;
            *) usage ;;
        esac
    done

    if [ $OPTIND -eq 1 ]; then
        usage
    fi
}

main "$@"
