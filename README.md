# WB 1.5 to ModRoom Mod Converter v1.0

A dedicated conversion tool that takes Wife's Bedroom v1.5 custom mods, Steam Workshop numeric folders, or unified `custom` directories and reorganizes them into the ModRoom mod architecture:
- `custom_futas/` (Lovers)
- `custom_wives/` (Partners / Spouses)
- `custom_bedrooms/` (Room Backgrounds)

---

## Quick Start (3 Steps)

1. Find your Wife's Bedroom v1.5 mod folder (or a mod `.zip` file).
2. Drag and drop that folder or `.zip` directly onto `Convert_1.5_to_ModRoom.bat`.
3. Press Enter when prompted.

Your converted mods will be ready in the `output/ModRoom_Mods` folder!

---

## What This Converter Does

### 1. Automatic Category Sorting
In Wife's Bedroom v1.5, all custom content is placed together inside a single `custom` folder. This tool inspects each mod pack's data headers and sorts them into their proper ModRoom categories:
- Mods with `.futa` data are routed to `custom_futas/` (Lovers).
- Mods with `.spouse` or `.wife` data are routed to `custom_wives/` (Partners).
- Mods with `.bedroom` data are routed to `custom_bedrooms/` (Room Backgrounds).

### 2. Resolves Steam Workshop Numbers into Real Names
Mods downloaded from the Steam Workshop often have confusing numeric folder names like `3821177370`.
This tool opens the internal data files, reads the character's real title (for example, "Ankha"), and renames the folder cleanly so you can easily recognize your characters in menus and on disk.

### 3. Disambiguates Name Collisions
If you have multiple mod packs with the same character name (for example, two different mods named "Ankha"), the tool safely appends the Workshop ID to prevent files from overwriting each other (e.g. `ankha_3821177370`).

### 4. Strips Unnecessary Art Project Files
Mod creators sometimes include large source art files (`.aseprite`, `.clip`, `.pdn`, `.kra`, `.psd`, `.zip`, and `.bak`).
This tool automatically filters out raw source files, keeping only game-ready images (`.png`), audio (`.ogg`, `.wav`, `.mp3`), and configuration files (`.ini`, `.futa`, `.json`) so your game stays fast and lightweight.

### 5. Generates Game-Ready Manifest Indexes
Generates clean `_manifest.txt` indexing files inside every converted folder so the mods load instantly in both desktop ModRoom and mobile APK builds.

---

## Prerequisites (What You Need on Your Computer)

This tool is lightweight and relies entirely on standard built-in tools:
- Python 3.8 or Higher: Download from [python.org](https://www.python.org/). During installation, make sure to check the box: "Add python.exe to PATH".
- Zero External Packages: No `pip install` commands or extra libraries are required.
- No Java Needed: Unlike the mobile APK patcher, this converter does not sign Android packages, so Java is not required.

---

## Ways to Use

### Method 1: Drag and Drop (Easiest)
Drag any v1.5 mod folder, your `wifes_bedroom_win1_5` game folder, or a mod `.zip` archive directly onto `Convert_1.5_to_ModRoom.bat`.

### Method 2: Use the "input" Folder
Drop your mod folders or `.zip` files into the `input` folder and double-click `Convert_1.5_to_ModRoom.bat`.

### Method 3: Merge Directly into Your ModRoom Game (Advanced)
You can point the converter directly at your existing ModRoom installation so converted mods are placed directly into your game folder:
```
python WB_1.5_to_ModRoom.py "path/to/v15_mods" --dest "path/to/ModRoom"
```

---

## Command Line Flags

| Flag | Purpose |
|---|---|
| `-d`, `--dest <path>` | Specify a custom destination folder (e.g. your ModRoom game directory). |
| `--clean` | Cleans target category folders before copying to ensure a fresh, clean export. |
| `-y`, `--yes` | Runs non-interactively without prompting (ideal for automated batch scripts). |

---

## Folder Layout

```
WB_1.5_to_ModRoom_Converter/
├── Convert_1.5_to_ModRoom.bat   (One-click Windows launcher)
├── WB_1.5_to_ModRoom.py         (Conversion engine)
├── README.md                    (This guide)
├── input/                       (Drop mod folders or .zip files here)
└── output/
    └── ModRoom_Mods/            (Converted game-ready mods)
        ├── custom_futas/
        ├── custom_wives/
        └── custom_bedrooms/
```
