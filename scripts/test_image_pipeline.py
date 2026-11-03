import argparse
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

SPEC = importlib.util.spec_from_file_location(
    "pipeline", Path(__file__).with_name("image_pipeline.py"))
PIPELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PIPELINE)


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.source = self.folder / "source.png"
        image = Image.new("RGB", (200, 100), "white")
        draw = ImageDraw.Draw(image)
        draw.line((20, 70, 80, 30, 140, 70), fill="black", width=2)
        draw.text((145, 60), "OH", fill="black")
        image.save(self.source)
        self.original = self.source.read_bytes()

    def tearDown(self):
        self.assertEqual(self.source.read_bytes(), self.original)
        self.temp.cleanup()

    def call(self, mode, output, **kwargs):
        return PIPELINE.run(argparse.Namespace(
            mode=mode, input=str(self.source), output=str(output), **kwargs))

    def test_original_preserves_bytes(self):
        output = self.folder / "copy.png"
        result = self.call("original", output)
        self.assertEqual(output.read_bytes(), self.original)
        self.assertEqual(result["sha256"], hashlib.sha256(self.original).hexdigest())

    def test_refuses_existing_output(self):
        with self.assertRaises(ValueError):
            self.call("original", self.source)
        output = self.folder / "exists.png"
        output.write_bytes(b"keep")
        with self.assertRaises(ValueError):
            self.call("enhance", output, scale=2)
        self.assertEqual(output.read_bytes(), b"keep")

    def test_enhance_dimensions(self):
        output = self.folder / "enhanced.png"
        result = self.call("enhance", output, scale=2)
        self.assertEqual(result["output_size"], (400, 200))
        with Image.open(output) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (400, 200))

    def test_transparency_preserved(self):
        transparent = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
        transparent.save(self.source)
        self.original = self.source.read_bytes()
        output = self.folder / "transparent.png"
        self.call("enhance", output, scale=2)
        with Image.open(output) as image:
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.getpixel((0, 0))[3], 0)

    def test_rejects_lossy_extension(self):
        output = self.folder / "bad.jpg"
        with self.assertRaises(ValueError):
            self.call("enhance", output, scale=2)
        self.assertFalse(output.exists())

    def test_chemistry_missing_dependency_is_explicit(self):
        if importlib.util.find_spec("rdkit"):
            self.skipTest("RDKit present; missing-dependency test not applicable")
        output = self.folder / "molecule.svg"
        with self.assertRaises(ModuleNotFoundError) as error:
            self.call("chemistry", output, smiles="CCO", molfile=None,
                      width=600, height=400, line_width=2, font_size=24, padding=.08)
        self.assertEqual(error.exception.name, "rdkit")
        self.assertFalse(output.exists())

    @unittest.skipUnless(importlib.util.find_spec("rdkit"), "RDKit not available")
    def test_chemistry_style_preserves_structure(self):
        import json
        import xml.etree.ElementTree as ET
        results = []
        for width in (400, 700):
            output = self.folder / f"molecule-{width}.svg"
            results.append(self.call("chemistry", output, smiles="C[C@H](O)C(=O)O",
                                     molfile=None, width=width, height=400,
                                     line_width=2, font_size=24, padding=.08))
            self.assertEqual(ET.parse(output).getroot().tag, "{http://www.w3.org/2000/svg}svg")
            data = json.loads(output.with_suffix(".svg.json").read_text())
            self.assertFalse(data["source_verified"])
        self.assertEqual(results[0]["structure_sha256"], results[1]["structure_sha256"])

    @unittest.skipUnless(importlib.util.find_spec("rdkit"), "RDKit not available")
    def test_chemistry_png_and_invalid_structure(self):
        output = self.folder / "molecule.png"
        self.call("chemistry", output, smiles="CCO", molfile=None,
                  width=600, height=400, line_width=2, font_size=24, padding=.08)
        with Image.open(output) as image:
            self.assertEqual(image.size, (600, 400))
        bad = self.folder / "bad.svg"
        with self.assertRaises(ValueError):
            self.call("chemistry", bad, smiles="not-a-molecule", molfile=None,
                      width=600, height=400, line_width=2, font_size=24, padding=.08)
        self.assertFalse(bad.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
