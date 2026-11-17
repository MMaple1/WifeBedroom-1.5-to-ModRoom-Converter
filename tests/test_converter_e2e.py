"""End-to-end tests for WB_1.5_to_Modded.py on synthetic packs.   Run: python -m unittest discover -s tests"""
import importlib.util, sys, tempfile, unittest, zipfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
import wbconv as W  # noqa: E402

spec = importlib.util.spec_from_file_location("v15_to_modded", ROOT / "WB_1.5_to_Modded.py")
CONV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CONV)


def strip(frames, fw, h=4):
    row = b"".join(bytes((10 * i + 10, 0, 0, 255)) * fw for i in range(frames))
    return W.Image(frames * fw, h, [bytearray(row) for _ in range(h)])


def png(folder, name, frames, fw=160):
    W.write_png(folder / name, strip(frames, fw))


def v15_partner(root, name, forward=True):
    d = Path(root) / "custom" / name
    d.mkdir(parents=True)
    for n, f, fw in (("custom_portrait.png", 10, 128), ("custom_mating_press.png", 4, 160), ("custom_reverse_cowgirl.png", 5, 160), ("custom_xray.png", 4, 160)):
        png(d, n, f, fw)
    if forward:
        png(d, "custom_forward_cowgirl.png", 6)
    (d / "custom_data.spouse").write_bytes(b'[info]\nname="' + name.encode() + b'"\n[sprite]\norigin_x="80"\norigin_y="84"\nxray_x="60"\nxray_y="90"\n')
    return d


def v15_lover(root, name, with_xray=True):
    d = Path(root) / "custom" / name
    d.mkdir(parents=True)
    for n, f, fw in (("custom_portrait.png", 10, 128), ("custom_mating_press.png", 9, 160), ("custom_reverse_cowgirl.png", 5, 160)):
        png(d, n, f, fw)
    if with_xray:
        png(d, "custom_xray.png", 3)
    (d / "custom_data.futa").write_bytes(b'[info]\nname="' + name.encode() + b'"\n[sprite]\norigin_x="80"\nxray_y="90"\n')
    return d


class V15ToModded(unittest.TestCase):
    def run_conv(self, src, dest, arch, **kw):
        kw.setdefault("verbose", False)
        kw.setdefault("quarantine_duplicates", False)
        return CONV.convert_15_to_modroom([Path(src)], Path(dest), target_arch=arch, **kw)

    def test_deeproom_export_is_standard_names_one_spouse_descriptor_with_pose_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "src", Path(tmp) / "dest"
            v15_partner(src, "Lisa")
            st = self.run_conv(src, dest, "deeproom")
            out = dest / "custom_stuff" / "custom_wives" / "lisa"
            names = {p.name for p in out.iterdir()}
            self.assertIn("custom_data.spouse", names)
            self.assertNotIn("custom_data.wife", names)
            self.assertTrue({"custom_mating_press.png", "custom_xray.png"} <= names)
            self.assertFalse(any(n.endswith("_0.png") for n in names))
            ini = W.Ini((out / "custom_data.spouse").read_bytes())
            self.assertEqual(ini.get("xray", "origin_x"), '"60"')
            self.assertIsNotNone(ini.get("mating_press", "origin_x"))
            self.assertEqual((out / "custom_data.spouse").read_text().lower().count("[sprite]"), 1)
            self.assertEqual(st["report"].counts(), {"ok": 1})

    def test_modroom_partner_is_padded_to_modern_frame_counts_with_one_wife_descriptor(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "src", Path(tmp) / "dest"
            v15_partner(src, "Lisa")
            self.run_conv(src, dest, "modroom")
            out = dest / "custom_wives" / "lisa"
            names = {p.name for p in out.iterdir()}
            self.assertEqual(W.png_size(out / "custom_wife_mating_press_0.png")[0], 5 * 160)
            self.assertEqual(W.png_size(out / "custom_wife_reverse_cowgirl_0.png")[0], 10 * 160)
            self.assertEqual(W.png_size(out / "custom_wife_cowgirl_0.png")[0], 11 * 160)
            self.assertEqual(W.png_size(out / "custom_wife_xray_0.png")[0], 4 * 160)   # .spouse pack: X-ray renamed, frames untouched
            self.assertIn("custom_data.wife", names)
            self.assertNotIn("custom_data.spouse", names)
            self.assertFalse({"custom_mating_press.png", "custom_xray.png"} & names)
            self.assertIn("custom_portrait.png", names)   # ModRoom reads a 10-frame portrait natively: kept as authored
            self.assertEqual(W.modroom_missing(out, "wife"), [])

    def test_modroom_aliases_a_missing_forward_cowgirl_instead_of_skipping(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "src", Path(tmp) / "dest"
            v15_partner(src, "NoForward", forward=False)
            st = self.run_conv(src, dest, "modroom")
            out = dest / "custom_wives" / "noforward"
            self.assertTrue((out / "custom_wife_cowgirl_0.png").exists())   # aliased from the reverse cowgirl
            self.assertEqual(W.modroom_missing(out, "wife"), [])
            self.assertEqual(st["skipped_packs"], 0)

    def test_modroom_lover_keeps_standard_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "src", Path(tmp) / "dest"
            v15_lover(src, "Bell")
            self.run_conv(src, dest, "modroom")
            out = dest / "custom_futas" / "bell"
            self.assertTrue((out / "custom_mating_press.png").exists())
            self.assertFalse((out / "custom_futa_mating_press_0.png").exists())
            self.assertEqual(W.Ini((out / "custom_data.futa").read_bytes()).get("sprite", "xray_offset_y"), '"6"')

    def test_modroom_lover_without_xray_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "src", Path(tmp) / "dest"
            v15_lover(src, "NoXray", with_xray=False)
            st = self.run_conv(src, dest, "modroom")
            self.assertEqual(st["report"].counts(), {"skipped": 1})

    def test_both_targets_with_dest_use_two_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "src", Path(tmp) / "dest"
            v15_partner(src, "Lisa")
            self.run_conv(src, dest, "both")
            # convert_15_to_modroom('both') writes custom_stuff/ (Deeproom) and the root categories (ModRoom) under one dest
            self.assertTrue((dest / "custom_stuff" / "custom_wives" / "lisa").is_dir())
            self.assertTrue((dest / "custom_wives" / "lisa").is_dir())

    def test_dry_run_and_clean_do_not_touch_the_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "src", Path(tmp) / "dest"
            v15_partner(src, "Lisa")
            self.run_conv(src, dest, "deeproom", dry_run=True)
            self.assertFalse(dest.exists())
            keep = dest / "custom_stuff" / "custom_wives" / "existing"
            keep.mkdir(parents=True)
            (keep / "custom_data.spouse").write_text("x")
            empty = Path(tmp) / "empty" / "custom"
            empty.mkdir(parents=True)
            self.run_conv(Path(tmp) / "empty", dest, "deeproom", clean_dest=True)
            self.assertTrue((keep / "custom_data.spouse").exists())

    def test_merge_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "src", Path(tmp) / "dest"
            v15_partner(src, "Lisa")
            self.run_conv(src, dest, "deeproom")
            mine = dest / "custom_stuff" / "custom_wives" / "lisa" / "mine.txt"
            mine.write_text("keep")
            self.run_conv(src, dest, "deeproom")
            self.assertTrue(mine.exists())
            self.assertTrue((dest / "custom_stuff" / "custom_wives" / "lisa_2").is_dir())

    def test_unsafe_zip_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            z = tmp / "bad.zip"
            with zipfile.ZipFile(z, "w") as zf:
                zf.writestr("../evil.txt", "x")
            CONV.convert_15_to_modroom([z], tmp / "dest", target_arch="deeproom", verbose=False, quarantine_duplicates=False)
            self.assertFalse((tmp / "evil.txt").exists())

    def test_no_pillow_needed(self):
        self.assertNotIn("PIL", (ROOT / "WB_1.5_to_Modded.py").read_text(encoding="utf-8"))


class ConsoleEncoding(unittest.TestCase):
    def test_printing_an_unencodable_pack_name_does_not_crash(self):
        import os, subprocess
        code = ("import importlib.util, sys; "
                "sys.path.insert(0, r'%s'); "
                "spec = importlib.util.spec_from_file_location('conv', r'%s'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); "
                "print('pack \\u221e name')" % (str(ROOT / "core"), str(ROOT / 'WB_1.5_to_Modded.py')))
        env = dict(os.environ, PYTHONIOENCODING="cp1252:strict")
        r = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))


if __name__ == "__main__":
    unittest.main()
