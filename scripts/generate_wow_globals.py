#!/usr/bin/env python3
"""
generate_wow_globals.py

Generates .luacheckrc containing:
 - WoW API globals (scraped from warcraft.wiki.gg)
 - FrameXML globals (parsed from Gethe's wow-ui-source zip, .lua files)
 - FrameXML XML names (parsed from .xml files; filtered)
 - GlobalStrings from Ketho's enUS.lua (handles NAME = ... and _G["NAME"] = ...)
 - custom globals from custom_globals.txt (one-per-line, '#' comments allowed)

Writes .luacheckrc in repo root (one level above this script).
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

API_WIKI_URL = "https://warcraft.wiki.gg/wiki/World_of_Warcraft_API"
FRAMEXML_ZIP_URL = "https://github.com/Gethe/wow-ui-source/archive/refs/heads/live.zip"
KETHO_GLOBALSTRINGS_RAW = "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/GlobalStrings/enUS.lua"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUTPUT_FILE = os.path.join(REPO_ROOT, ".luacheckrc")
CUSTOM_GLOBALS_PATH = os.path.join(REPO_ROOT, "custom_globals.txt")

# Patterns used for parsing .lua files
PATTERNS = [
    re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*="),     # NAME = ...
    re.compile(r"^\s*_G\[['\"]([A-Za-z0-9_]+)['\"]\]\s*="), # _G["NAME"] = ...
    re.compile(r"^\s*_G\.([A-Za-z_][A-Za-z0-9_]*)\s*="), # _G.NAME = ...
    re.compile(r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("), # function NAME(
]

# Filter for XML-extracted names: only letters, digits, underscores (allow leading digits).
XML_NAME_ALLOWED = re.compile(r"^[A-Za-z0-9_]+$")


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
    print("Downloading FrameXML source zip from Gethe's repo...")
    resp = requests.get(FRAMEXML_ZIP_URL, timeout=60)
    resp.raise_for_status()

    tmpdir = tempfile.TemporaryDirectory()
    zip_path = os.path.join(tmpdir.name, "framexml.zip")
    with open(zip_path, "wb") as f:
        f.write(resp.content)

    print("Extracting FrameXML zip...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(tmpdir.name)

    # Optional: print top-level entries for debugging
    # print("Extracted top-level:", os.listdir(tmpdir.name))
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
    """
    Stream-parse FrameXML .xml files and collect 'name' attribute values.
    Filter names to only letters/digits/underscore (allows numeric-leading names).
    """
    print("Parsing FrameXML .xml files for named UI objects...")
    names: set[str] = set()
    xml_count = 0
    matched = 0

    for root, _, files in os.walk(extracted_path):
        for fname in files:
            if not fname.endswith(".xml"):
                continue
            fpath = os.path.join(root, fname)
            xml_count += 1
            try:
                # Use iterparse to keep memory low
                for event, elem in ET.iterparse(fpath, events=("start",)):
                    name_attr = elem.get("name")
                    if name_attr:
                        name_attr = name_attr.strip()
                        if XML_NAME_ALLOWED.match(name_attr):
                            names.add(name_attr)
                            matched += 1
                    # clear element to free memory
                    elem.clear()
            except ET.ParseError:
                # Some XML files may contain constructs ElementTree dislikes; skip them
                print(f"  Warning: XML parse error in {fpath}, skipping.")
            except Exception as e:
                print(f"  Warning: Could not read {fpath}: {e}")

    print(f"  Scanned {xml_count} XML files, matched {len(names)} valid names (total matches {matched}).")
    return names


def fetch_globalstrings_globals_ketho() -> set[str]:
    print("Fetching enUS.lua global strings from Ketho's repo...")
    resp = requests.get(KETHO_GLOBALSTRINGS_RAW, timeout=30)
    resp.raise_for_status()

    globals_set: set[str] = set()
    # Patterns: NAME = ...   and   _G["NAME"] = ...
    p_simple = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=")
    p_g = re.compile(r'^\s*_G\["([^"]+)"\]\s*=')
    for line in resp.text.splitlines():
        m1 = p_simple.match(line)
        if m1:
            globals_set.add(m1.group(1))
            continue
        m2 = p_g.match(line)
        if m2:
            # only accept simple names (letters/digits/underscore)
            name = m2.group(1).strip()
            if XML_NAME_ALLOWED.match(name):
                globals_set.add(name)
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
    lines: list[str] = [
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
        '11./SLASH_.*',  # Setting an undefined (Slash handler) global variable
        '11./BINDING_.*',  # Setting an undefined (Keybinding header) global variable
        '113/LE_.*',  # Accessing an undefined (Lua ENUM type) global variable
        '113/NUM_LE_.*',  # Accessing an undefined (Lua ENUM type) global variable
        '211',  # Unused local variable
        '211/L',  # Unused local variable "L"
        '211/CL',  # Unused local variable "CL"
        '212',  # Unused argument
        '213',  # Unused loop variable
        '214',  # Unused hint
        # '231',  # Set but never accessed (commented out)
        '311',  # Value assigned to a local variable is unused
        '314',  # Value of a field in a table literal is unused
        '42.',  # Shadowing a local variable, an argument, a loop variable.
        '43.',  # Shadowing an upvalue, an upvalue argument, an upvalue loop variable.
        '542',  # An empty if branch
        '581',  # Error-prone operator orders
        '582',  # Error-prone operator orders
    ]
    for p in ignore_patterns:
        lines.append(f"    '{p}',")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    try:
        api_globals = fetch_api_globals()
    except Exception as e:
        print(f"Error fetching API globals: {e}")
        api_globals = set()

    # Download & extract FrameXML once
    tmpdir = None
    try:
        tmpdir = download_and_extract_framexml()
        extracted_path = tmpdir.name
        lua_framexml_globals = parse_framexml_lua_globals(extracted_path)
        xml_names = parse_framexml_xml_names(extracted_path)
    except Exception as e:
        print(f"Error handling FrameXML zip: {e}")
        lua_framexml_globals = set()
        xml_names = set()
    finally:
        if tmpdir:
            tmpdir.cleanup()

    try:
        globalstrings_globals = fetch_globalstrings_globals_ketho()
    except Exception as e:
        print(f"Error fetching Ketho GlobalStrings: {e}")
        globalstrings_globals = set()

    custom_globals = read_custom_globals()

    # Merge all
    all_globals = api_globals | lua_framexml_globals | xml_names | globalstrings_globals | custom_globals

    new_content = generate_luacheckrc_content(all_globals)

    # Write only if changed
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            current = f.read()
        if current == new_content:
            print("No changes to .luacheckrc. Exiting.")
            # print count for GitHub Actions if desired
            print(len(all_globals))
            sys.exit(0)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Wrote {len(all_globals)} globals to {OUTPUT_FILE}.")
    print(len(all_globals))  # last line useful for GH Actions parsing


if __name__ == "__main__":
    main()
