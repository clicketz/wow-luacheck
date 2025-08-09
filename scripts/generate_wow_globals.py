#!/usr/bin/env python3
import os
import re
import json
import requests
from slpp import slpp as lua

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_LUACHECK = os.path.join(REPO_ROOT, ".luacheckrc")
OUTPUT_LUA = os.path.join(REPO_ROOT, "wow_globals.lua")
OUTPUT_JSON = os.path.join(REPO_ROOT, "wow_globals.json")
CUSTOM_GLOBALS_PATH = os.path.join(REPO_ROOT, "custom_globals.txt")
COMMIT_MSG_PATH = os.path.join(REPO_ROOT, "commit_message.txt")
PREV_GLOBALS_PATH = os.path.join(REPO_ROOT, "prev_globals.txt")

BASE_URL = "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/"
GLOBAL_STRINGS_URL = "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/GlobalStrings/enUS.lua"

FILES_TO_PARSE = {
    "Events.lua": "table",
    "FrameXML.lua": "table",
    "Frames.lua": "table",
    "GlobalAPI.lua": "table",
    "LuaEnum.lua": "table",
    "Mixins.lua": "table",
    "WidgetAPI.lua": "table",
}

def fetch_url(url):
    print(f"Downloading {url} ...")
    r = requests.get(url)
    r.raise_for_status()
    return r.text

def extract_globals_from_table(table_obj):
    """
    Recursively extract globals and fields from a Lua table parsed as Python dict or list.
    Returns:
      globals_dict = { global_name: {"fields": [field1, field2, ...]}, ... }
    """
    globals_dict = {}

    if isinstance(table_obj, dict):
        for k, v in table_obj.items():
            if isinstance(v, dict):
                fields = []
                for subk in v.keys():
                    if isinstance(subk, str):
                        fields.append(subk)
                globals_dict[k] = {"fields": sorted(fields)}
            else:
                globals_dict[k] = None

    elif isinstance(table_obj, list):
        # If it's a list, assume each item is a global name string or a dict
        for item in table_obj:
            if isinstance(item, str):
                globals_dict[item] = None
            elif isinstance(item, dict):
                # Possibly dict with single key?
                for k, v in item.items():
                    if isinstance(v, dict):
                        fields = []
                        for subk in v.keys():
                            if isinstance(subk, str):
                                fields.append(subk)
                        globals_dict[k] = {"fields": sorted(fields)}
                    else:
                        globals_dict[k] = None
            else:
                # unknown type, ignore
                pass

    else:
        print(f"Warning: Unexpected table_obj type: {type(table_obj)}")

    return globals_dict

def parse_lua_table_file(content):
    """
    Find first big Lua table in file content and parse with slpp.
    Returns dict of globals extracted.
    """
    import re

    # Try to find first "= {...}" assignment block
    pattern = re.compile(r'=\s*({.*})', re.DOTALL)
    match = pattern.search(content)
    if not match:
        # fallback: try to find standalone table literal
        pattern2 = re.compile(r'({.*})', re.DOTALL)
        match2 = pattern2.search(content)
        if not match2:
            print("No table literal found for parsing.")
            return {}
        table_str = match2.group(1)
    else:
        table_str = match.group(1)

    # Remove Lua comments
    table_str = re.sub(r'--\[\[.*?\]\]', '', table_str, flags=re.DOTALL)
    table_str = re.sub(r'--.*', '', table_str)

    # slpp expects well-formed Lua table, so remove trailing commas & whitespace if needed

    try:
        table_obj = lua.decode(table_str)
    except Exception as e:
        print(f"Failed to parse Lua table: {e}")
        return {}

    return extract_globals_from_table(table_obj)

def parse_globalstrings(lua_text):
    """
    Parse global strings from _G["GLOBAL_NAME"] = "some string" pattern.
    Returns set of global names.
    """
    pattern = re.compile(r'_G\[\s*["\']([^"\']+)["\']\s*\]\s*=')
    return set(pattern.findall(lua_text))

def read_custom_globals():
    if not os.path.isfile(CUSTOM_GLOBALS_PATH):
        print(f"No custom globals file found at {CUSTOM_GLOBALS_PATH}, skipping.")
        return {}, set()

    globals_dict = {}
    simple_globals = set()
    with open(CUSTOM_GLOBALS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if '.' in line:
                tbl, fld = line.split('.', 1)
                if tbl not in globals_dict:
                    globals_dict[tbl] = {"fields": set()}
                if "fields" not in globals_dict[tbl]:
                    globals_dict[tbl]["fields"] = set()
                globals_dict[tbl]["fields"].add(fld)
            else:
                simple_globals.add(line)
    for k in globals_dict:
        globals_dict[k]["fields"] = sorted(globals_dict[k]["fields"])
    return globals_dict, simple_globals

def merge_globals(dicts_list, simple_sets_list):
    merged_dict = {}
    merged_simple = set()

    for d in dicts_list:
        for k, v in d.items():
            if v is None:
                merged_simple.add(k)
            else:
                if k not in merged_dict:
                    merged_dict[k] = {"fields": set()}
                if "fields" in v:
                    merged_dict[k]["fields"].update(v["fields"])

    for s in simple_sets_list:
        merged_simple.update(s)

    for k in merged_dict:
        merged_dict[k]["fields"] = sorted(merged_dict[k]["fields"])

    merged_simple.difference_update(merged_dict.keys())

    return merged_dict, merged_simple

def format_luacheck_globals(globals_dict, simple_globals):
    lines = []
    for g in sorted(simple_globals):
        lines.append(f'    "{g}",')

    for g in sorted(globals_dict.keys()):
        lines.append(f'    {g} = {{')
        lines.append('        fields = {')
        for f in globals_dict[g]["fields"]:
            lines.append(f'            "{f}",')
        lines.append('        },')
        lines.append('    },')

    return "\n".join(lines)

def generate_luacheckrc(globals_dict, simple_globals):
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
        "ignore = {",
    ]
    lines.extend(ignore_lines)
    lines.append("}")
    lines.append("")
    lines.append("globals = {")
    lines.append(format_luacheck_globals(globals_dict, simple_globals))
    lines.append("}")
    lines.append("")
    return "\n".join(lines)

def generate_lua_globals_list(globals_dict, simple_globals):
    all_globals = set(simple_globals)
    all_globals.update(globals_dict.keys())
    lines = ["return {"]
    for g in sorted(all_globals):
        lines.append(f'    "{g}",')
    lines.append("}")
    lines.append("")
    return "\n".join(lines)

def generate_json_globals_list(globals_dict, simple_globals):
    all_globals = set(simple_globals)
    all_globals.update(globals_dict.keys())
    return json.dumps(sorted(all_globals), indent=2)

def load_prev_globals():
    if os.path.isfile(PREV_GLOBALS_PATH):
        with open(PREV_GLOBALS_PATH, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def write_commit_message(added, removed):
    msg = f"chore: update WoW globals list (added: {added}, removed: {removed})\n"
    with open(COMMIT_MSG_PATH, "w", encoding="utf-8") as f:
        f.write(msg)

def main():
    globals_dicts = []
    simple_globals_sets = []

    for filename, parse_type in FILES_TO_PARSE.items():
        url = BASE_URL + filename
        try:
            content = fetch_url(url)
        except Exception as e:
            print(f"Warning: failed to download {filename}: {e}")
            continue

        if parse_type == "table":
            globals_dict = parse_lua_table_file(content)
            globals_dicts.append(globals_dict)
            print(f"Parsed {len(globals_dict)} globals from {filename}")

    # Parse GlobalStrings/enUS.lua separately for string globals
    try:
        globalstrings_content = fetch_url(GLOBAL_STRINGS_URL)
        gs_globals = parse_globalstrings(globalstrings_content)
        simple_globals_sets.append(gs_globals)
        print(f"Parsed {len(gs_globals)} globals from GlobalStrings/enUS.lua")
    except Exception as e:
        print(f"Warning: failed to download or parse GlobalStrings/enUS.lua: {e}")

    # Read custom globals
    custom_dict, custom_simple = read_custom_globals()
    globals_dicts.append(custom_dict)
    simple_globals_sets.append(custom_simple)
    print(f"Read {len(custom_simple)} custom simple globals and {len(custom_dict)} custom globals with fields")

    # Merge all globals
    merged_dict, merged_simple = merge_globals(globals_dicts, simple_globals_sets)
    print(f"Total globals after merge: {len(merged_simple)} simple + {len(merged_dict)} with fields")

    # Compare with previous run to track additions/removals
    merged_all = set(merged_simple) | set(merged_dict.keys())
    prev_globals = load_prev_globals()

    added = len(merged_all - prev_globals)
    removed = len(prev_globals - merged_all)

    write_commit_message(added, removed)

    # Save current globals for next run
    with open(PREV_GLOBALS_PATH, "w", encoding="utf-8") as f:
        for g in sorted(merged_all):
            f.write(g + "\n")

    # Write outputs
    with open(OUTPUT_LUACHECK, "w", encoding="utf-8") as f:
        f.write(generate_luacheckrc(merged_dict, merged_simple))
    print(f"Wrote {OUTPUT_LUACHECK}")

    with open(OUTPUT_LUA, "w", encoding="utf-8") as f:
        f.write(generate_lua_globals_list(merged_dict, merged_simple))
    print(f"Wrote {OUTPUT_LUA}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        f.write(generate_json_globals_list(merged_dict, merged_simple))
    print(f"Wrote {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
