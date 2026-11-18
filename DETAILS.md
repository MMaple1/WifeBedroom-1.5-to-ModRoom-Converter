# WB 1.5 to Modded Mod Converter v1.2 — Technical Details

Converts **Wife's Bedroom v1.5** custom mods (the unified `custom/` folder, individual packs, `.zip` files or Steam Workshop downloads) into the split-category layouts of **Deeproom 4.0.3 Kiwami** and **ModRoom v3.3**:

- `custom_futas/` (lovers), `custom_wives/` (partners), `custom_bedrooms/` (rooms)
- Deeproom: inside a `custom_stuff/` container. ModRoom: root category folders.

Standard library only (Python 3.8 or newer). No Pillow.

---

## What Each Target Gets

v1.5 partner packs use the same format as Deeproom's `.spouse` packs, and ModRoom's partner format is the modern one with different frame counts:

### Frame Count Comparison Table

| Strip | v1.5 / Deeproom standard | ModRoom `_0.png` |
|---|---|---|
| Lover portrait / mating press / cowgirl / X-ray | 10 / 9 / 5 / 3 frames | (ModRoom reads the standard names natively) |
| Partner portrait | 10 | 17 |
| Partner mating press | 4 | 5 |
| Partner reverse cowgirl | 5 | 10 |
| Partner forward cowgirl | 6 | 11 |
| Partner X-ray | 4 | 3 |

Frames are usually 160 px wide and portrait frames 128 px, but the games cut a strip into a fixed number of frames whatever its width, so high-res packs (e.g. 256 px portraits, 220 px mating-press frames) convert the same way. The lover's standard cowgirl strip is 5 frames, or 7 when it is 7 frames of 160 px. A strip whose width does not divide into its frame count is reported and left as it is.

---

## Target-Specific Rules and Descriptor Mapping

### Deeproom
Standard names and **one descriptor** per pack (`custom_data.futa` / `custom_data.spouse`). Nothing is renamed or resized. Missing keys are added without touching existing ones:
- Pose blocks `[mating_press]` and `[reverse_cowgirl]` from the `[sprite]` origins.
- `[xray]` from v1.5's `xray_x/xray_y` (80/84 when absent, as v1.5 draws it; the body's origin is never copied into `[xray]`).
- `[deepthroat] origin_y` only from v1.5's `deepthroat_origin_y`, minus 70 (Deeproom draws partner deepthroat 70 px higher). Without that key no `[deepthroat]` block is written and the game uses the `[sprite]` origin, as for native Deeproom packs.
- `[condom]`, `[gender] is_male`, and `[sprite] xray_offset_y`.

### ModRoom
- **Lovers**: Keep their standard names (ModRoom reads them natively) with one `custom_data.futa`; `[sprite] xray_offset_y` is added.
- **Partners**: Get `custom_wife_*_0.png` strips and **one** `custom_data.wife`:
  - Mating press (4 to 5), reverse cowgirl (5 to 10), forward cowgirl (6 to 11) are **padded** with transparent frames (nothing dropped; the added frames are blank, so an animation can briefly show an empty frame).
  - The X-ray (4 to 3) is **not** converted by default and the 10-frame portrait is kept as it is (ModRoom reads it natively): the X-ray crop drops a frame (hybrid packs show the standard 4th frame equal to the modern 3rd) and the portrait is a layered face strip.
  - `--approximate` also pads the portrait to 17 frames and crops the X-ray (first 3 frames kept), but the X-ray only for packs that already have a `custom_data.wife`; a v1.5 `.spouse` pack keeps its X-ray as authored, renamed to `custom_wife_xray_0.png` with its 4 frames.
  - The standard-named strips are removed from the pack.
- **ModRoom's Own Rules**: ModRoom lists a pack only if it has the sprites it draws, otherwise it crashes.
  - A lover needs portrait, mating press, cowgirl, and X-ray.
  - A partner needs mating press, forward cowgirl, and reverse cowgirl.
  - A partner that only has a reverse cowgirl gets it copied (padded) as the forward one (`custom_reverse_cowgirl.png` auto-aliases and pads to 11 frames as `custom_wife_cowgirl_0.png` so no wives are purged).
  - A pack that still lacks required assets is **skipped** and the report names it.

A strip whose width is not a whole number of frames is left alone and reported.

---

## Safety and File Handling

- **Staging.** Packs are converted in a temporary folder; the destination is only touched once at least one pack was produced. `--clean` removes the old category folders at that point, not before.
- **No overwriting, no piling up of copies.** Running the converter again into the same folder skips packs that are already there unchanged. A pack with the same name but different content is added next to the old one with the tag that tells them apart (or `_2` as a last resort).
- **`--dry-run`** writes only the report.
- **Zip files** are checked for paths that would write outside the temporary folder; an unsafe archive is skipped, and temporary folders are removed even after an error.
- **Duplicates** are skipped and listed in the report; nothing is copied into a `!duplicates` folder.
- **Duplicate Quarantine Category Isolation**: `custom_futas` (Lovers/Tops) and `custom_wives` (Partners/Bottoms) are strictly isolated and never match as duplicates. Bypasses generic placeholder names (`"example"`, `"partner"`, `"wife"`) in Tier 1 duplicate clustering.

---

## Additional Features

- **Real-Time Visual Progress Bar**: Displays dynamic percentage and current character pack name during batch conversions so the terminal never appears stalled.
- **Interactive Approximate Gating**: Lossy frame reduction is gated behind an interactive `[y/N]` prompt (defaulting safely to No) and `--no-approximate` / `--approximate` CLI flags.
- **Reverse Cowgirl Fallback Aliasing & Padding**: v1.5 partner packs with only `custom_reverse_cowgirl.png` (81% of v1.5 partners) automatically alias and pad to 11 frames as `custom_wife_cowgirl_0.png` for ModRoom v3.3.
- **Non-Destructive Portrait Preservation**: ModRoom v3.3 natively reads 10-frame portraits via `legacy_custom_portrait`; 10-frame portraits are kept intact instead of unlinked.
- **Guaranteed Output Directory Creation**: Destination category directories (`custom_futas`, `custom_wives`, `custom_bedrooms`) and their `_manifest.txt` indexes are guaranteed to be created.
- **Steam Workshop names**: numeric folders (for example `3821177370`) are named from the pack's `[info] name`.
- **Loose portrait mapping**: a single unnumbered `*portrait*.png` becomes `custom_portrait.png` when a pack has none.
- **Raw art files** (`.aseprite`, `.clip`, `.psd`, `.blend`, `.bak`) are not copied.
- **`_manifest.txt`** index files are written, sorted alphabetically, for PC and Android.

---

## Report Statuses

The conversion report `output/conversion_report.md` details outcomes per pack and target architecture:
- **ok / exact**: Converted cleanly without modifications or frame drops.
- **padded**: Transparent frames appended to match required strip lengths (e.g. partner mating press and cowgirl animations for ModRoom).
- **approximate**: Dropped frames under `--approximate` to fit modern expectations.
- **skipped**: Mod pack omitted due to missing essential sprites (ModRoom crash prevention), duplicates, or path safety rejections, with the rationale explicitly noted.

---

## Full Command-Line Options

```
usage: WB_1.5_to_Modded.py [-h] [-t {deeproom,modroom,both}] [-d DEST]
                           [--clean] [--approximate] [--no-approximate]
                           [--dry-run] [-y] [--quarantine-duplicates]
                           [--no-quarantine-duplicates]
                           [inputs ...]

positional arguments:
  inputs                Path(s) to v1.5 mod folders, custom/ directory,
                        character packs, or .zip archives.

options:
  -h, --help            show this help message and exit
  -t {deeproom,modroom,both}, --target {deeproom,modroom,both}
                        Target output architecture: deeproom (standard
                        naming), modroom (v3.3 _0.png naming), or both.
  -d DEST, --dest DEST  Destination directory (ModRoom/Deeproom game folder or
                        export folder).
  --clean               Clean destination category folders before converting.
  --approximate         Also convert strips whose frame counts differ by
                        dropping frames (first N kept); listed as
                        'approximate' in the report.
  --no-approximate      Disallow lossy frame reduction (default: safe)
  --dry-run             Convert into a temporary folder and write only the
                        report; nothing is written to the destination.
  -y, --yes             Non-interactive execution (accept defaults).
  --quarantine-duplicates
                        Automatically detect and quarantine duplicate custom
                        character/room folders (default: True)
  --no-quarantine-duplicates
                        Disable duplicate custom folder quarantine
```

Note: With `-d DEST` and `-t both`, exports are written to `DEST/Deeproom_Mods` and `DEST/ModRoom_Mods`.

---

## Tests and the Shared Module

`python -m unittest discover -s tests` runs the tests.

The conversion core is `core/wbconv.py`. **Four identical copies exist** (both converters, the WB Mobile Patcher's `wbp/wbconv.py` and the Custom Studio's `backend/wbconv.py`): edit the one in `Modded_to_WB_1.5_Converter_v1.1/core/` and run the patcher's `python tools/sync_wbconv.py` (`--check` only reports).

---

## Limits

- Padding keeps all content but adds blank frames; the animation of a padded strip may show an empty frame. Check converted partners in ModRoom.
- v1.5's separate `custom_eyes.png` / `custom_mouth.png` overlays are not baked into portraits for the older engines.
- Nothing here was tested in the game; the output files were checked for frame counts, descriptors and structure.
