#!/usr/bin/env python3
"""
generate_wow_globals.py (no-cache version)

Downloads FrameXML zip and Ketho enUS.lua each run, parses:
 - API globals (warcraft.wiki.gg)
 - FrameXML .lua globals
 - FrameXML .xml 'name' attributes (streamed)
 - Ketho enUS.lua (NAME = ... and _G["NAME"] = ...)
 - custom_globals.txt (optional)

Outputs:
 - .luacheckrc
 - wow_globals.lua
 - wow_globals.json

Writes files only if content changed.
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

API_WIKI_URL = "https://warcraft.wiki.gg/wiki/World_of_Warcraft_API"
FRAMEXML_ZIP_URL = "https://github.com/Gethe/wow-ui-source/archive/refs/heads/live.zip"
KETHO_GLOBALSTRINGS_RAW = "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/GlobalStrings/enUS.lua"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
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

XML_NAME_ALLOWED = re.compile(r"^[A-Za-z0-9_]+$")  # allow letters, digits, underscores


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


def download_and_extract_framexml() -> tempfile.TemporaryDirectory:
    print("Downloading FrameXML zip from Gethe's repo...")
    resp = requests.get(FRAMEXML_ZIP_URL, timeout=90)
    resp.raise_for_status()
    tmpdir = tempfile.TemporaryDirectory()
    zip_path = os.path.join(tmpdir.name, "framexml.zip")
    with open(zip_path, "wb") as f:
        f.write(resp.content)
    print("Extracting FrameXML zip...")
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
    print(f"  Found {len(globals_set)} globals from .lua files.")
    return globals_set


def parse_framexml_xml_names(extracted_path: str) -> set[str]:
    print("Parsing FrameXML .xml files for named UI objects (streamed)...")
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
    print("Fetching enUS.lua global strings from Ketho's repo...")
    resp = requests.get(KETHO_GLOBALSTRINGS_RAW, timeout=30)
    resp.raise_for_status()
    globals_set: set[str] = set()
    p_simple = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=")
    p_g = re.compile(r'^\s*_G\["([^"]+)"\]\s*=')
    for line in resp.text.splitlines():
        m1 = p_simple.match(line)
        if m1:
            globals_set.add(m1.group(1))
            continue
        m2 = p_g.match(line)
        if m2:
            nm = m2.group(1).strip()
            if XML_NAME_ALLOWED.match(nm):
                globals_set.add(nm)
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


def write_if_changed(path: str, content: str) -> bool:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            if f.read() == content:
                return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def main() -> None:
    all_globals: set[str] = se_
