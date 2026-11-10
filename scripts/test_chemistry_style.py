"""Real RDKit rendering checks for the optional chemistry presentation preset."""
import argparse
from pathlib import Path
import tempfile
import unittest

from PIL import Image
try:
    from rdkit import Chem
    from rdkit.Chem import rdMolDescriptors
except ModuleNotFoundError:
    Chem = None
    rdMolDescriptors = None
import image_pipeline


@unittest.skipUnless(Chem is not None, "RDKit not available")
class ChemistryStyle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def render(self, name, smiles="Cc1ccccc1", **options):
        values = dict(mode="chemistry", smiles=smiles, molfile=None,
                      output=str(self.root / name), width=600, height=420,
                      line_width=2.5, font_size=28, padding=.2,
                      style="standard", explicit_methyl=False)
        values.update(options)
        return image_pipeline.run(argparse.Namespace(**values))

    def test_style_preserves_structure(self):
        plain = self.render("plain.svg")
        memo = self.render("memo.svg", style="memo", explicit_methyl=True)
        self.assertEqual(plain["structure_sha256"], memo["structure_sha256"])
        self.assertEqual(memo["methyl_labels"], 1)
        self.assertFalse(memo["source_verified"])
        molecule = Chem.MolFromSmiles(memo["canonical_smiles"])
        self.assertEqual(rdMolDescriptors.CalcMolFormula(molecule), "C7H8")
        self.assertEqual(sum(a.GetIsAromatic() for a in molecule.GetAtoms()), 6)
        svg = Path(memo["output"]).read_text(encoding="utf-8")
        self.assertIn("#176B53", svg.upper())

    def test_png_palette_dimensions_and_whitespace(self):
        result = self.render("memo.png", style="memo", explicit_methyl=True)
        with Image.open(result["output"]) as image:
            self.assertEqual(image.size, (600, 420))
            self.assertEqual(image.convert("RGB").getpixel((0, 0)), (247, 251, 249))
            self.assertGreater(len(image.getcolors(600 * 420)), 1)

    def test_no_overwrite(self):
        result = self.render("keep.svg")
        original = Path(result["output"]).read_bytes()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.render("keep.svg", style="memo")
        self.assertEqual(Path(result["output"]).read_bytes(), original)

    def test_isotopes_are_not_hidden(self):
        result = self.render("isotope.svg", smiles="[13CH3]c1ccccc1",
                             explicit_methyl=True)
        self.assertEqual(result["methyl_labels"], 0)
        self.assertIn("13", result["canonical_smiles"])

    def test_label_opt_in(self):
        result = self.render("standard.svg")
        self.assertEqual(result["methyl_labels"], 0)
        self.assertEqual(result["style"], "standard")


if __name__ == "__main__":
    unittest.main()
