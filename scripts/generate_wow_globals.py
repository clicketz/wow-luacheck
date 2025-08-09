import requests
from bs4 import BeautifulSoup
import re
import os
import sys
import tempfile
import zipfile

API_WIKI_URL = "https://warcraft.wiki.gg/wiki/World_of_Warcraft_API"
FRAMEXML_ZIP_URL = "https://github.com/Gethe/wow-ui-source/archive/refs/heads/live.zip"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUTPUT_FILE = os.path.join(REPO_ROOT, ".luacheckrc")

PATTERNS = [
    re.compile(r"^\s*(\w+)\s*="),
    re.compile(r"^\s*_G\[['\"](\w+)['\"]\]\s*="),
    re.compile(r"^\s*_G\.(\w+)\s*="),
    re.compile(r"^\s*function\s+(\w+)\s*\("),
]

def fetch_api_globals():
    print("Fetching WoW API globals from warcraft.wiki.gg...")
    resp = requests.get(API_WIKI_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    globals_found = set()
    for a in soup.select('a[href^="/wiki/API_"]'):
        name = a.text.strip()
        if name:
            globals_found.add(name)
    print(f"Found {len(globals_found)} API globals.")
    return globals_found

def download_and_extract_framexml():
    print("Downloading FrameXML source zip from GitHub...")
    resp = requests.get(FRAMEXML_ZIP_URL)
    resp.raise_for_status()

    tmpdir = tempfile.TemporaryDirectory()
    zip_path = os.path.join(tmpdir.name, "framexml.zip")
    with open(zip_path, "wb") as f:
        f.write(resp.content)

    print("Extracting FrameXML zip...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(tmpdir.name)

    return tmpdir  # caller must cleanup with tmpdir.cleanup()

def parse_framexml_globals(extracted_path):
    print("Parsing FrameXML globals...")
    globals_set = set()
    for root, _, files in os.walk(extracted_path):
        for fname in files:
            if fname.endswith(".lua"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, encoding="utf-8", errors="ignore") as fh:
                        for line in fh:
                            for pattern in PATTERNS:
                                m = pattern.match(line)
                                if m:
                                    globals_set.add(m.group(1))
                except Exception as e:
                    print(f"Warning: Skipping {fpath} due to error: {e}")
    print(f"Found {len(globals_set)} FrameXML globals.")
    return globals_set

def parse_globalstrings_globals(extracted_path):
    print("Parsing GlobalStrings.lua globals...")
    globals_set = set()
    for root, _, files in os.walk(extracted_path):
        for fname in files:
            if fname == "GlobalStrings.lua":
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, encoding="utf-8", errors="ignore") as fh:
                        for line in fh:
                            m = re.match(r"^\s*(\w+)\s*=", line)
                            if m:
                                globals_set.add(m.group(1))
                except Exception as e:
                    print(f"Warning: Could not parse {fpath}: {e}")
    print(f"Found {len(globals_set)} globals in GlobalStrings.lua")
    return globals_set

def read_custom_globals():
    custom_globals_path = os.path.join(REPO_ROOT, "custom_globals.txt")
    if not os.path.exists(custom_globals_path):
        print(f"No custom globals file found at {custom_globals_path}, skipping.")
        return set()
    globals_set = set()
    with open(custom_globals_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue  # skip blank lines and comments
            globals_set.add(stripped)
    print(f"Loaded {len(globals_set)} custom globals from {custom_globals_path}.")
    return globals_set

def generate_luacheckrc_content(globals_list):
    sorted_globals = sorted(globals_list)
    lines = [
        "std = 'lua51'",
        "max_line_length = false",
        "exclude_files = {'**Libs/', '**libs/'}",
        "",
        "globals = {"
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
    for pattern in ignore_patterns:
        lines.append(f"    '{pattern}',")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)

def main():
    api_globals = fetch_api_globals()

    tmpdir = download_and_extract_framexml()
    try:
        framexml_globals = parse_framexml_globals(tmpdir.name)
        globalstrings_globals = parse_globalstrings_globals(tmpdir.name)
    finally:
        tmpdir.cleanup()

    custom_globals = read_custom_globals()
    all_globals = api_globals | framexml_globals | globalstrings_globals | custom_globals
    new_content = generate_luacheckrc_content(all_globals)

    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            current_content = f.read()
        if current_content == new_content:
            print("No changes to .luacheckrc. Exiting.")
            sys.exit(0)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Wrote {len(all_globals)} globals to {OUTPUT_FILE}.")
    print(len(all_globals))  # For GitHub Actions output parsing

if __name__ == "__main__":
    main()
