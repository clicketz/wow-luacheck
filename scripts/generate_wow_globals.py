#!/usr/bin/env python3
"""
generate_wow_globals.py

- Caches downloads in REPO_ROOT/.cache/
- Uses conditional GET (ETag / Last-Modified) to avoid re-downloading unchanged files
- Parses:
  * warcraft.wiki.gg API links
  * FrameXML .lua files (from Gethe zip)
  * FrameXML .xml names (streamed)
  * Ketho enUS.lua (GlobalStrings)
  * custom_globals.txt
- Outputs:
  * .luacheckrc (repo root)
  * wow_globals.lua (repo root) - contains `globals = { ... }`
  * wow_globals.json (repo root) - JSON array of globals
"""
from __future__ import annotations
import requests
from bs4 import BeautifulSoup
import re
import os
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
import json
from typing import Optional, Tuple

# Sources
API_WIKI_URL = "https://warcraft.wiki.gg/wiki/World_of_Warcraft_API"
FRAMEXML_ZIP_URL = "https://github.com/Gethe/wow-ui-source/archive/refs/heads/live.zip"
KETHO_GLOBALSTRINGS_RAW = "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/GlobalStrings/enUS.lua"

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
CACHE_DIR = os.path.join(REPO_ROOT, ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

OUTPUT_LUACHECK = os.path.join(REPO_ROOT, ".luacheckrc")
OUTPUT_WOW_LUA = os.path.join(REPO_ROOT, "wow_globals.lua")
OUTPUT_WOW_JSON = os.path.join(REPO_ROOT, "wow_globals.json")
CUSTOM_GLOBALS_PATH = os.path.join(REPO_ROOT, "custom_globals.txt")

# Patterns for Lua parsing
PATTERNS = [
    re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*="),         # NAME = ...
    re.compile(r"^\s*_G\[['\"]([A-Za-z0-9_]+)['\"]\]\s*="),  # _G["NAME"] = ...
    re.compile(r"^\s*_G\.([A-Za-z_][A-Za-z0-9_]*)\s*="),    # _G.NAME = ...
    re.compile(r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("), # function NAME(
]

XML_NAME_ALLOWED = re.compile(r"^[A-Za-z0-9_]+$")  # allow letters, digits, underscores, leading digits ok


# -----------------------------
# Helper: conditional HTTP GET with local cache metadata
# -----------------------------
def cached_get(url: str, cache_basename: str, timeout: int = 30) -> Tuple[int, str, Optional[dict]]:
    """
    Download `url` with cache stored under CACHE_DIR/cache_basename.
    Returns (status_code, path_to_file, headers_dict_or_None).
    - If cached and server returns 304, returns 304 and local file path.
    - If download/replace, returns actual status and local file path.
    """
    cache_file = os.path.join(CACHE_DIR, cache_basename)
    meta_file = cache_file + ".meta"

    headers = {}
    # load metadata if present
    if os.path.exists(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as mf:
                meta = json.load(mf)
                etag = meta.get("etag")
                lm = meta.get("last_modified")
                if etag:
                    headers["If-None-Match"] = etag
                if lm:
                    headers["If-Modified-Since"] = lm
        except Exception:
            # ignore meta parse errors
            pass

    resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
    if resp.status_code == 304 and os.path.exists(cache_file):
        # Not modified; return existing file
        return 304, cache_file, resp.headers
    if resp.status_code != 200:
        # propagate errors (caller should handle)
        resp.raise_for_status()

    # Write content to temp file then move
    tmp_path = cache_file + ".tmp"
    with open(tmp_path, "wb") as out_f:
        for chunk in resp.iter_content(chunk_size=1024 * 64):
            if chunk:
                out_f.write(chunk)
    os.replace(tmp_path, cache_file)

    # Save metadata (ETag and Last-Modified if present)
    meta = {}
    etag_h = resp.headers.get("ETag")
    lm_h = resp.headers.get("Last-Modified")
    if etag_h:
        meta["etag"] = etag_h
    if lm_h:
        meta["last_modified"] = lm_h
    try:
        with open(meta_file, "w", encoding="utf-8") as mf:
            json.dump(meta, mf)
    except Exception:
        pass

    return resp.status_code, cache_file, resp.headers


# -----------------------------
# Fetch / parse functions
# -----------------------------
def fetch_api_globals() -> set[str]:
    print("Fetching WoW API globals from warcraft.wiki.gg...")
    resp = requests.get(API_WIKI_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    globals_found: set[str] = set()
    for a in soup.select('a[href^="/wiki/API_"]'):
        name = a.text.strip()
        if name:
            globals_found.add(name)
    print(f"  Found {len(globals_found)} API globals.")
    return globals_found


def download_and_extract_framexml_once() -> tempfile.TemporaryDirectory:
    """Download framexml zip using cache and extract to a temp dir; return TemporaryDirectory."""
    print("Downloading FrameXML (cached) from Gethe's repo...")
    status, zip_path, headers = cached_get(FRAMEXML_ZIP_URL, "framexml_live.zip", timeout=90)
    # extract into a new temp dir
    tmpdir = tempfile.TemporaryDirectory()
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(tmpdir.name)
    return tmpdir


def parse_framexml_lua_globals(extracted_path: str) -> set[str]:
    print("Parsing FrameXML .lua files for globals...")
    globals_set: set[str] = set()
    for root, _, files in os.walk(extracted_path):
        for fname in files:
            if not fname.endswith(".lua"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        for pattern in PATTERNS:
                            m = pattern.match(line)
                            if m:
                                globals_set.add(m.group(1))
            except Exception as e:
                print(f"  Warning: Skipping {fpath} due to error: {e}")
    print(f"  Found {len(globals_set)} globals from .lua.")
    return globals_set


def parse_framexml_xml_names(extracted_path: str) -> set[str]:
    print("Parsing FrameXML .xml files for named UI objects (streaming)...")
    names: set[str] = set()
    xml_count = 0
    matched_total = 0
    for root, _, files in os.walk(extracted_path):
        for fname in files:
            if not fname.endswith(".xml"):
                continue
            xml_count += 1
            fpath = os.path.join(root, fname)
            try:
                for event, elem in ET.iterparse(fpath, events=("start",)):
                    name_attr = elem.get("name")
                    if name_attr:
                        name_attr = name_attr.strip()
                        if XML_NAME_ALLOWED.match(name_attr):
                            names.add(name_attr)
                            matched_total += 1
                    elem.clear()
            except ET.ParseError:
                print(f"  Warning: XML parse error in {fpath}, skipping.")
            except Exception as e:
                print(f"  Warning: Could not read {fpath}: {e}")
    print(f"  Scanned {xml_count} XML files, matched {len(names)} unique names (total matches {matched_total}).")
    return names


def fetch_globalstrings_globals_ketho() -> set[str]:
    print("Fetching Ketho enUS.lua (cached)...")
    status, file_path, headers = cached_get(KETHO_GLOBALSTRINGS_RAW, "ketho_enUS.lua", timeout=30)
    globals_set: set[str] = set()
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            p_simple = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=")
            p_g = re.compile(r'^\s*_G\["([^"]+)"\]\s*=')
            for line in fh:
                m1 = p_simple.match(line)
                if m1:
                    globals_set.add(m1.group(1))
                    continue
                m2 = p_g.match(line)
                if m2:
                    nm = m2.group(1).strip()
                    if XML_NAME_ALLOWED.match(nm):
                        globals_set.add(nm)
    except Exception as e:
        print(f"  Warning: Could not read cached Ketho file: {e}")
    print(f"  Found {len(globals_set)} globals in enUS.lua.")
    return globals_set


def read_custom_globals() -> set[str]:
    if not os.path.exists(CUSTOM_GLOBALS_PATH):
        print("No custom_globals.txt found; skipping.")
        return set()
    globals_set: set[str] = set()
    with open(CUSTOM_GLOBALS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            globals_set.add(s)
    print(f"  Loaded {len(globals_set)} custom globals from custom_globals.txt.")
    return globals_set


# -----------------------------
# Output generation
# -----------------------------
def generate_luacheckrc_content(globals_list: set[str]) -> str:
    sorted_globals = sorted(globals_list)
    lines = [
        "std = 'lua51'",
        "max_line_length = false",
        "exclude_files = {'**Libs/', '**libs/'}",
        "",
        "globals = {",
    ]
    for name in sorted_globals:
        lines.append(f"    '{name}',")
    lines.append("}")
    lines.append("")
    lines.append("ignore = {")
    ignore_patterns = [
        '11./SLASH_.*',
        '11./BINDING_.*',
        '113/LE_.*',
        '113/NUM_LE_.*',
        '211',
        '211/L',
        '211/CL',
        '212',
        '213',
        '214',
        # '231',
        '311',
        '314',
        '42.',
        '43.',
        '542',
        '581',
        '582',
    ]
    for p in ignore_patterns:
        lines.append(f"    '{p}',")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def generate_wow_globals_lua(globals_list: set[str]) -> str:
    """Create a Lua file that sets globals = { ... } for dofile usage."""
    sorted_globals = sorted(globals_list)
    lines = ["-- Auto-generated by scripts/generate_wow_globals.py", "globals = {"]
    for name in sorted_globals:
        lines.append(f'    "{name}",')
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def generate_wow_globals_json(globals_list: set[str]) -> str:
    sorted_globals = sorted(globals_list)
    return json.dumps(sorted_globals, indent=2, ensure_ascii=False) + "\n"


# -----------------------------
# Main
# -----------------------------
def main() -> None:
    all_globals: set[str] = set()
    try:
        api_globals = fetch_api_globals()
        all_globals |= api_globals
    except Exception as e:
        print(f"Error fetching API globals: {e}")

    # Download & extract FrameXML once (cached)
    tmpdir = None
    try:
        tmpdir = download_and_extract_framexml_once()
        extracted_path = tmpdir.name
        try:
            lua_framexml_globals = parse_framexml_lua_globals(extracted_path)
            all_globals |= lua_framexml_globals
        except Exception as e:
            print(f"Error parsing FrameXML Lua files: {e}")
        try:
            xml_names = parse_framexml_xml_names(extracted_path)
            all_globals |= xml_names
        except Exception as e:
            print(f"Error parsing FrameXML XML files: {e}")
    except Exception as e:
        print(f"Error downloading/extracting FrameXML zip: {e}")
    finally:
        if tmpdir:
            tmpdir.cleanup()

    try:
        globalstrings = fetch_globalstrings_globals_ketho()
        all_globals |= globalstrings
    except Exception as e:
        print(f"Error fetching GlobalStrings from Ketho: {e}")

    # custom globals if present (user can still supply extras they want treated as programmatic)
    try:
        custom = read_custom_globals()
        all_globals |= custom
    except Exception as e:
        print(f"Error reading custom_globals.txt: {e}")

    # Generate outputs
    luacheck_content = generate_luacheckrc_content(all_globals)
    wow_lua_content = generate_wow_globals_lua(all_globals)
    wow_json_content = generate_wow_globals_json(all_globals)

    # Write files only if changed (to avoid noisy commits)
    def write_if_changed(path: str, content: str) -> bool:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                if f.read() == content:
                    return False
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    changed = False
    changed |= write_if_changed(OUTPUT_LUACHECK, luacheck_content)
    changed |= write_if_changed(OUTPUT_WOW_LUA, wow_lua_content)
    changed |= write_if_changed(OUTPUT_WOW_JSON, wow_json_content)

    print(f"Wrote {len(all_globals)} globals to files (changed={changed}).")
    # last line: count (useful for GH Actions)
    print(len(all_globals))


if __name__ == "__main__":
    main()
