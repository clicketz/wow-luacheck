import requests
from bs4 import BeautifulSoup
import re
import os
import sys

API_URL = "https://raw.githubusercontent.com/Gethe/wow-ui-source/live/Blizzard_APIDocumentation/Blizzard_APIDocumentation.lua"
FRAMEXML_URL = "https://raw.githubusercontent.com/Gethe/wow-ui-source/live/FrameXML"

OUTPUT_FILE = "wow_globals.lua"

def fetch_api_globals():
    print("Fetching WoW API globals...")
    resp = requests.get(API_URL)
    resp.raise_for_status()
    text = resp.text

    globals_found = re.findall(r'name\s*=\s*"([A-Za-z_][A-Za-z0-9_]*)"', text)
    return set(globals_found)

def fetch_framexml_globals():
    print("Fetching FrameXML globals...")
    globals_set = set()

    resp = requests.get(FRAMEXML_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.endswith(".lua"):
            file_url = f"{FRAMEXML_URL}/{href}"
            lua_text = requests.get(file_url).text
            matches = re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", lua_text, flags=re.M)
            globals_set.update(matches)

    return globals_set

def generate_luacheckrc_entry(globals_list):
    sorted_globals = sorted(globals_list)
    lines = ["globals = {"]
    for name in sorted_globals:
        lines.append(f'    "{name}",')
    lines.append("}")
    return "\n".join(lines) + "\n"

def main():
    api_globals = fetch_api_globals()
    framexml_globals = fetch_framexml_globals()
    all_globals = api_globals | framexml_globals
    lua_output = generate_luacheckrc_entry(all_globals)

    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            current_content = f.read()
        if current_content == lua_output:
            print("No changes to globals list. Exiting.")
            sys.exit(0)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(lua_output)

    print(f"Wrote {len(all_globals)} globals to {OUTPUT_FILE}.")
    # Exit with globals count so workflow can use it
    print(len(all_globals))

if __name__ == "__main__":
    main()
