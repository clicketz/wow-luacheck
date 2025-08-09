import requests
from bs4 import BeautifulSoup
import re
import os
import sys

API_WIKI_URL = "https://warcraft.wiki.gg/wiki/World_of_Warcraft_API"
FRAMEXML_ZIP_URL = "https://github.com/Gethe/wow-ui-source/archive/refs/heads/live.zip"

# Calculate repo root and .luacheckrc output file path
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

def fetch_framexml_globals():
    print("Downloading FrameXML source from GitHub...")
    resp = requests.get(FRAMEXML_ZIP_URL)
    resp.raise_for_status()

    import tempfile
    import zipfile

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "framexml.zip")
        with open(zip_path, "wb") as f:
            f.write(resp.content)

        print("Extracting FrameXML...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tmpdir)

        globals_set = set()
        for root, _, files in os.walk(tmpdir):
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

def generate_luacheckrc_content(globals_list):
    sorted_globals = sorted(globals_list)
    lines = [
        'std = "none"',
        "",
        "globals = {"
    ]
    for name in sorted_globals:
        lines.append(f'    "{name}",')
    lines.append("}")
    return "\n".join(lines) + "\n"

def main():
    api_globals = fetch_api_globals()
    framexml_globals = fetch_framexml_globals()
    all_globals = api_globals | framexml_globals
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
