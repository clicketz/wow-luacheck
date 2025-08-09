#!/usr/bin/env python3
import os
import re
import requests
import json

# Constants for repo root and output files
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_LUA = os.path.join(REPO_ROOT, "wow_globals.lua")
OUTPUT_LUACHECK = os.path.join(REPO_ROOT, ".luacheckrc")
OUTPUT_JSON = os.path.join(REPO_ROOT, "wow_globals.json")
CUSTOM_GLOBALS_PATH = os.path.join(REPO_ROOT, "custom_globals.txt")

# URL for GlobalStrings enUS.lua from Ketho's repo (always latest mainline)
GLOBALSTRINGS_URL = "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/GlobalStrings/enUS.lua"

def fetch_globalstrings():
    print(f"Downloading GlobalStrings from {GLOBALSTRINGS_URL} ...")
    r = requests.get(GLOBALSTRINGS_URL)
    r.raise_for_status()
    return r.text

def parse_globalstrings(lua_text):
    """
    Parse global strings names from the Lua file.

    Matches patterns:
      NAME = "string"
      _G["NAME"] = "string"
      _G['NAME'] = 'string'
    Extract only NAME parts.
    """
    globals_found = set()

    # Pattern for simple assignment: NAME = "..."
    pattern_simple = re.compile(r'^(\w+)\s*=\s*["\'].*?["\']', re.MULTILINE)

    # Pattern for _G["NAME"] = "..."
    pattern_g = re.compile(r'_G\[\s*["\']([^"\']+)["\']\s*\]\s*=\s*["\'].*?["\']')

    # Find simple assignments
    for match in pattern_simple.finditer(lua_text):
        name = match.group(1)
        globals_found.add(name)

    # Find _G["NAME"] style assignments
    for match in pattern_g.finditer(lua_text):
        name = match.group(1)
        globals_found.add(name)

    return globals_found

def read_custom_globals():
    """
    Read custom globals from custom_globals.txt

    - Strip comments (lines starting with #)
    - Strip whitespace
    - Ignore empty lines
    """
    if not os.path.isfile(CUSTOM_GLOBALS_PATH):
        print(f"No custom globals file found at {CUSTOM_GLOBALS_PATH}, skipping.")
        return set()

    print(f"Reading custom globals from {CUSTOM_GLOBALS_PATH} ...")
    custom_globals = set()
    with open(CUSTOM_GLOBALS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            custom_globals.add(line)
    return custom_globals

def generate_lua_globals_file(globals_list):
    """
    Generate a Lua file defining the globals list in a Lua table.

    Format:
    return {
      "GLOBAL1",
      "GLOBAL2",
      ...
    }
    """
    lines = ['return {']
    for g in sorted(globals_list):
        lines.append(f'    "{g}",')
    lines.append('}')
    return "\n".join(lines) + "\n"

def generate_luacheckrc(globals_list):
    """
    Generate a minimal .luacheckrc snippet that marks globals as read-only.

    Format:

    globals = {
      "GLOBAL1",
      "GLOBAL2",
      ...
    }

    Also includes your desired options like std, max_line_length, exclude_files, ignore
    """
    ignore_lines = [
        '    \'11./SLASH_.*\', -- Setting an undefined (Slash handler) global variable',
        '    \'11./BINDING_.*\', -- Setting an undefined (Keybinding header) global variable',
        '    \'113/LE_.*\', -- Accessing an undefined (Lua ENUM type) global variable',
        '    \'113/NUM_LE_.*\', -- Accessing an undefined (Lua ENUM type) global variable',
        '    \'211\', -- Unused local variable',
        '    \'211/L\', -- Unused local variable "L"',
        '    \'211/CL\', -- Unused local variable "CL"',
        '    \'212\', -- Unused argument',
        '    \'213\', -- Unused loop variable',
        '    \'214\', -- Unused hint',
        '    -- \'231\', -- Set but never accessed',
        '    \'311\', -- Value assigned to a local variable is unused',
        '    \'314\', -- Value of a field in a table literal is unused',
        '    \'42.\', -- Shadowing a local variable, an argument, a loop variable.',
        '    \'43.\', -- Shadowing an upvalue, an upvalue argument, an upvalue loop variable.',
        '    \'542\', -- An empty if branch',
        '    \'581\', -- Error-prone operator orders',
        '    \'582\', -- Error-prone operator orders',
    ]

    lines = [
        "std = 'lua51'",
        "max_line_length = false",
        "exclude_files = {'**Libs/', '**libs/'}",
        "ignore = {"
    ]
    lines.extend(ignore_lines)
    lines.append("}")
    lines.append("")
    lines.append("globals = {")
    for g in sorted(globals_list):
        lines.append(f'    "{g}",')
    lines.append("}")
    lines.append("")

    return "\n".join(lines)

def generate_json_globals(globals_list):
    """Generate JSON representation."""
    return json.dumps(sorted(globals_list), indent=2)

def main():
    try:
        lua_text = fetch_globalstrings()
    except Exception as e:
        print(f"ERROR: Failed to download GlobalStrings.lua: {e}")
        return 1

    globals_set = parse_globalstrings(lua_text)
    custom_globals = read_custom_globals()

    combined_globals = globals_set.union(custom_globals)

    # Write wow_globals.lua
    lua_content = generate_lua_globals_file(combined_globals)
    with open(OUTPUT_LUA, "w", encoding="utf-8") as f:
        f.write(lua_content)
    print(f"Wrote {OUTPUT_LUA} with {len(combined_globals)} globals.")

    # Write .luacheckrc
    luacheck_content = generate_luacheckrc(combined_globals)
    with open(OUTPUT_LUACHECK, "w", encoding="utf-8") as f:
        f.write(luacheck_content)
    print(f"Wrote {OUTPUT_LUACHECK} with {len(combined_globals)} globals.")

    # Write wow_globals.json
    json_content = generate_json_globals(combined_globals)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        f.write(json_content)
    print(f"Wrote {OUTPUT_JSON} with {len(combined_globals)} globals.")

    # Print total count (for GitHub Actions to capture)
    print(len(combined_globals))

    return 0

if __name__ == "__main__":
    exit(main())
