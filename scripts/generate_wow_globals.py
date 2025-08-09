#!/usr/bin/env python3
import os
import re
import json
import requests

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_LUACHECK = os.path.join(REPO_ROOT, ".luacheckrc")
OUTPUT_LUA = os.path.join(REPO_ROOT, "wow_globals.lua")
OUTPUT_JSON = os.path.join(REPO_ROOT, "wow_globals.json")
CUSTOM_GLOBALS_PATH = os.path.join(REPO_ROOT, "custom_globals.txt")

BASE_URL = "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/"
GLOBAL_STRINGS_URL = "https://raw.githubusercontent.com/Ketho/BlizzardInterfaceResources/mainline/Resources/GlobalStrings/enUS.lua"

FILES_TO_PARSE = {
    "Events.lua": "events",
    "FrameXML.lua": "global_vars_and_functions",
    "Frames.lua": "simple_table",
    "GlobalAPI.lua": "global_vars_and_functions",
    "LuaEnum.lua": "simple_table",
    "Mixins.lua": "global_vars_and_functions",
    "WidgetAPI.lua": "global_vars_and_functions",
}

def fetch_url(url):
    print(f"Downloading {url} ...")
    r = requests.get(url)
    r.raise_for_status()
    return r.text

def parse_simple_table(lua_text):
    pattern = re.compile(r'(\w+)\s*=\s*["\'].*?["\']')
    keys = set(m.group(1) for m in pattern.finditer(lua_text))
    return keys

def parse_events(lua_text):
    return parse_simple_table(lua_text)

def parse_global_vars_and_functions(lua_text):
    globals_dict = {}

    func_pattern = re.compile(r'function\s+(\w+)\s*\(')
    for match in func_pattern.finditer(lua_text):
        globals_dict[match.group(1)] = None

    assign_pattern = re.compile(r'^(\w+)\s*=\s*[^{}"\']', re.MULTILINE)
    for match in assign_pattern.finditer(lua_text):
        name = match.group(1)
        if name not in globals_dict:
            globals_dict[name] = None

    table_pattern = re.compile(r'(\w+)\s*=\s*{([^}]*)}', re.DOTALL)
    for match in table_pattern.finditer(lua_text):
        global_name = match.group(1)
        content = match.group(2)
        field_pattern = re.compile(r'(\w+)\s*=')
        fields = list(set(f.group(1) for f in field_pattern.finditer(content)))
        if fields:
            globals_dict[global_name] = {"fields": sorted(fields)}
        else:
            globals_dict[global_name] = None

    return globals_dict

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

def main():
    globals_dicts = []
    simple_globals_sets = []

    # Parse all FILES_TO_PARSE
    for filename, parse_type in FILES_TO_PARSE.items():
        url = BASE_URL + filename
        try:
            content = fetch_url(url)
        except Exception as e:
            print(f"Warning: failed to download {filename}: {e}")
            continue

        if parse_type == "simple_table":
            keys = parse_simple_table(content)
            simple_globals_sets.append(keys)
            print(f"Parsed {len(keys)} simple globals from {filename}")
        elif parse_type == "events":
            keys = parse_events(content)
            simple_globals_sets.append(keys)
            print(f"Parsed {len(keys)} event globals from {filename}")
        elif parse_type == "global_vars_and_functions":
            d = parse_global_vars_and_functions(content)
            globals_dicts.append(d)
            print(f"Parsed {len(d)} globals with possible fields from {filename}")

    # Parse GlobalStrings/enUS.lua separately
    try:
        globalstrings_content = fetch_url(GLOBAL_STRINGS_URL)
        gs_globals = parse_globalstrings(globalstrings_content)
        simple_globals_sets.append(gs_globals)
        print(f"Parsed {len(gs_globals)} globals from GlobalStrings/enUS.lua")
    except Exception as e:
        print(f"Warning: failed to download or parse GlobalStrings/enUS.lua: {e}")

    # Read custom globals file
    custom_dict, custom_simple = read_custom_globals()
    globals_dicts.append(custom_dict)
    simple_globals_sets.append(custom_simple)
    print(f"Read {len(custom_simple)} custom simple globals and {len(custom_dict)} custom globals with fields")

    # Merge all globals
    merged_dict, merged_simple = merge_globals(globals_dicts, simple_globals_sets)
    print(f"Total globals after merge: {len(merged_simple)} simple + {len(merged_dict)} with fields")

    # Write .luacheckrc
    with open(OUTPUT_LUACHECK, "w", encoding="utf-8") as f:
        f.write(generate_luacheckrc(merged_dict, merged_simple))
    print(f"Wrote {OUTPUT_LUACHECK}")

    # Write wow_globals.lua
    with open(OUTPUT_LUA, "w", encoding="utf-8") as f:
        f.write(generate_lua_globals_list(merged_dict, merged_simple))
    print(f"Wrote {OUTPUT_LUA}")

    # Write JSON output
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        f.write(generate_json_globals_list(merged_dict, merged_simple))
    print(f"Wrote {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
