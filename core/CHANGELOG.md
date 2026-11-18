# Changelog: WB 1.5 to Modded Mod Converter

All notable changes to the **WB 1.5 to Modded Mod Converter** tool are documented in this file.

---

## [Version 1.2.1] - 2026-11-17

### Fixes
- **Deeproom partners' deepthroat drawn too high.** Converting a partner for Deeproom added `[deepthroat] origin_y="150"` (v1.5's default) when the pack had no deepthroat height, so Deeproom drew the sprite 66 px above the `[sprite]` origin its own packs use; a real v1.5 `deepthroat_origin_y` was copied unchanged, 70 px too high (Deeproom draws partner deepthroat 70 px higher than v1.5). Now no block is written without a v1.5 value, and a v1.5 value becomes Deeproom's value minus 70.
- **`Repair_Deepthroat.bat` / `Repair_Deepthroat.py`** fix partners converted with an earlier version: blocks in exactly the old converter's shape are removed or corrected, everything else is left alone, dry run first, originals backed up to a zip.

---

## [Version 1.2.0] - 2026-11-16

### Highlights
- **No more `_2` copies.** Converting again into a folder that already holds a pack no longer makes a second numbered copy: an unchanged pack is skipped (generated `_manifest.txt` files are ignored in the comparison). Packs that share a display name keep the tag from their folder name (`astolfo_(naked)`) instead of a doubled or numbered name.
- **Robustness.** Pack folder names are made filesystem-safe (a name that crashed the run with WinError 123 is handled, with a fallback to the pack folder name or a hash); a corrupt PNG no longer aborts the whole conversion; a folder that fails to copy is not reported as written; a stray non-folder input is skipped; `--no-approximate` is honoured and the approximate question is asked once. The README starts with a plain-language quick guide.
- ModRoom partners are padded to ModRoom's real frame counts (mating press 5, reverse cowgirl 10, forward cowgirl 11; the X-ray 4 to 3 crop is `--approximate` only). The old step padded to 9 and 4 frames, which did not match ModRoom's 24 and 5, and every other strip was renamed without any padding.
- One descriptor per pack: Deeproom gets `custom_data.spouse` / `.futa` with standard names; ModRoom gets `custom_data.wife` with `_0.png` strips, and lovers keep their standard names, which ModRoom reads natively. The old output wrote both `.spouse` and `.wife` and both naming sets in the same folder.
- ModRoom exports skip packs that lack a sprite ModRoom draws (it would crash), and say which.
- Pillow is no longer needed: it was imported unconditionally at the top of the script.

### Added
- **Learned frame maps for `--approximate`** (`FRAME_MAPS` in `core/wbconv.py`): found by comparing the frames of community packs that ship both formats for the same character. Lover mating press 24 to 9 keeps modern frames 0-7 and 19, lover cowgirl 19 to 5 keeps 0, 1, 2, 14, 17, partner mating press 5 to 4 keeps 0-3; other strips keep their first N frames and portraits are never mapped. Small samples (4 and 10 packs), reported as approximate.
- **Shared, tested conversion core (`core/wbconv.py`)**, identical in both converters, standard library only: PNG reading/writing with pad and crop (replaces Pillow), the frame-count tables measured from thousands of packs, descriptor conversion that only adds keys, ModRoom V3.3's admission rules, safe zip extraction and a conversion report.
- **Staged output.** Packs are converted in a temporary folder and published only if at least one was produced. `--clean` no longer empties the destination before anything has been found, and merging never overwrites an existing pack (`name_2`).
- **`--dry-run`** (report only) and **`--approximate`** (keep the first N frames where frame counts differ), and an `output/conversion_report.md` listing every pack as ok / padded / approximate / partial / skipped with the reason.
- **Safe zip extraction** (paths that would escape the temporary folder are rejected) and temporary folders are always removed.
- **Duplicate packs are skipped and listed, not copied** into a `!duplicates` folder.
- Tests: `python -m unittest discover -s tests`.
- `-t both` with `-d` now exports to `DEST/Deeproom_Mods` and `DEST/ModRoom_Mods` (it used to export Deeproom only).

### Changed
- Deeproom descriptors get their pose blocks, `[condom]`, `[gender]` and `[sprite] xray_offset_y` through the additive editor, using v1.5's `xray_x/xray_y` and `deepthroat_origin_y` when present.
- Removed the step that pasted v1.5's eyes and mouth overlays onto portrait frame 0 (it needed Pillow and did not match how the engines cut portraits).

### Fixed
- `hashlib` was used but never imported, which silently switched off the identical-asset duplicate check.
- `[info]` / `[sprite]` handling no longer rewrites or appends blindly (a duplicate `[sprite]` header and a destructive regex over the whole descriptor are gone).
- The duplicate-scoring step ignored the chosen target architecture.

## [Version 1.1.0] - 2026-11-13

### Highlights
- Implementation of the **3-Tier Duplicate Detection & Quarantine Pipeline** preventing duplicate character clones.
- Introduction of **Dual Architecture Target Export** (`--target deeproom | modroom | both`).
- Implementation of the **Universal Wife Recognition Shield** and cowgirl fallback architecture.
- Recursive multi-depth mod pack discovery engine.
- Steam Workshop numeric ID resolution and collision disambiguation.
- ModRoom v3.3 frame divisor slicing math and transparent padding cures.

### Added
- **Deeproom 4.0.3 Kiwami Export Architecture (`-t deeproom` / `-t both`)**:
  * Added export support targeting Deeproom 4.0.3's `custom_stuff/` root directory container.
  * Injects Deeproom 4.0.3 pose-specific origin blocks (`[mating_press]`, `[reverse_cowgirl]`, `[deepthroat]`, `[xray]`) into `.wife` and `.spouse` files.
  * Guarantees `[personality]` (`climax="1.00"`, `womb_fill="1.00"`) and `[gender]` (`is_male="0"`) descriptors are synthesized during deconstruction.
  * Full bi-directional sprite mapping creates both `_0.png` format and standard formats for deepthroat and xray poses.
- **3-Tier Cross-Folder & Multi-Content Duplicate Detection Engine**:
  * Detects cross-category duplicates and multi-content redundancies (bedrooms, SFX, music).
  * Isolates redundant duplicates into **`output/!duplicates/`**.
  * Scans source packs prior to conversion; groups duplicate folders via name/metadata (Tier 1) and sprite SHA-256 hashes (Tier 2).
  * Isolates redundant duplicates into `output/!duplicates/<category>/` with `DUPLICATES_REPORT.txt` (Tier 3).
  * Prevents cluttering output with unnecessary `_1`, `_2` collision clones.
  * Added `--quarantine-duplicates` (default True) and `--no-quarantine-duplicates` CLI flags.
- **Dual Architecture Target Export**:
  - **`[1] Deeproom 4.0 Standard`** (`output/Deeproom_Mods/`): Standard canonical unnumbered filenames (`custom_portrait.png`, `custom_mating_press.png`, `custom_data.spouse`, `custom_data.futa`).
  - **`[2] ModRoom v3.3 Legacy`** (`output/ModRoom_Mods/`): Legacy `_0.png` filenames (`custom_futa_portrait_0.png`, `custom_wife_portrait_0.png`, `custom_data.wife`).
  - **`[3] Both`** (Interactive default, exports both architectures simultaneously side-by-side).
- **Universal Wife Recognition Shield (`Universal Wife Shield`)**:
  - Automatically identifies spouse/partner packs even when missing descriptor headers by analyzing sprite dimensions, aspect ratios, and frame structures.
  - Automatically maps missing cowgirl/reverse cowgirl frames to base mating press frames, eliminating GameMaker runtime crashes.
- **ModRoom Frame Divisor Slicing Math**:
  - Dynamically calculates sheet widths and injects transparent padding for 5, 10, 11, and 17 frame sprite sheets so ModRoom v3.3 slices at exactly 160.0 px.
- **Steam Workshop Numeric ID Resolution**:
  - Inspects internal INI `[info] name=` to convert raw numeric IDs (e.g. `3821177370`) into human-readable character names.
- **Safe Collision Disambiguation**:
  - Appends deduplication tags if multiple packs share the same character name, preventing file clobbering.
- **Recursive Pack Discovery Engine (`discover_all_packs`)**:
  - Traverses nested subdirectories, multi-pack bundles, and extracted zip folders without early-exit limitations.

### Changed & Improved
- **Interactive Target Selector**:
  - Added intuitive prompt menu with `[3] Both` pre-selected as the default on Enter.
- **Command Line Flags**:
  - Added `-t, --target {deeproom,modroom,both}` and `--clean`.

---

## [Version 1.0.0] - Baseline Release

### Features
- Initial release of the WB 1.5 to ModRoom deconstruction tool.
- Single-target export to legacy ModRoom v3.3 `_0.png` format.
- Basic category separation into `custom_futas/`, `custom_wives/`, and `custom_bedrooms/`.
