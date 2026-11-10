"""Memo-Canvas local image helpers. No network, recognition, or publishing."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def reserve(path):
    if path.exists():
        raise ValueError(f"Refusing to overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)


def run(args):
    output = Path(args.output).resolve()
    if args.mode in ("original", "enhance"):
        source = Path(args.input).resolve(strict=True)
        if source == output:
            raise ValueError("Output must differ from source")
    reserve(output)
    if args.mode == "original":
        shutil.copyfile(source, output)
        return {"mode": "original", "output": str(output),
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    if args.mode == "enhance":
        from PIL import Image, ImageFilter, ImageOps
        if output.suffix.lower() != ".png":
            raise ValueError("Enhancement output must be PNG")
        with Image.open(source) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise ValueError("Multi-frame input is not supported")
            if image.width * image.height * args.scale ** 2 > 40_000_000:
                raise ValueError("Output exceeds 40 megapixel safety limit")
            image = ImageOps.exif_transpose(image)
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            original_size = image.size
            image = image.resize((image.width * args.scale, image.height * args.scale),
                                 Image.Resampling.LANCZOS)
            image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=3))
            image.save(output, format="PNG")
        return {"mode": "enhance", "input_size": original_size,
                "output_size": image.size, "output": str(output),
                "note": "Traditional interpolation and mild sharpening; no recovered semantics"}
    from rdkit import Chem
    from rdkit.Chem.Draw import rdMolDraw2D
    if output.suffix.lower() not in (".svg", ".png"):
        raise ValueError("Chemistry output must be SVG or PNG")
    metadata = output.with_suffix(output.suffix + ".json")
    reserve(metadata)
    if not (100 <= args.width <= 4096 and 100 <= args.height <= 4096):
        raise ValueError("Canvas dimensions must be 100..4096")
    if not (0 <= args.padding <= .4 and 0 < args.line_width <= 10 and 6 <= args.font_size <= 96):
        raise ValueError("Invalid drawing parameters")
    mol = Chem.MolFromSmiles(args.smiles) if args.smiles else Chem.MolFromMolFile(args.molfile)
    if mol is None or mol.GetNumAtoms() == 0:
        raise ValueError("Invalid or empty molecular structure")
    canonical = Chem.MolToSmiles(mol, isomericSmiles=True)
    drawer_type = rdMolDraw2D.MolDraw2DSVG if output.suffix.lower() == ".svg" else rdMolDraw2D.MolDraw2DCairo
    drawer = drawer_type(args.width, args.height)
    options = drawer.drawOptions()
    options.bondLineWidth = args.line_width
    options.fixedFontSize = args.font_size
    options.padding = args.padding
    style = getattr(args, "style", "standard")
    explicit_methyl = getattr(args, "explicit_methyl", False)
    if style == "memo":
        # Memo-inspired local preset, not an official brand specification.
        ink = (23 / 255, 107 / 255, 83 / 255)
        options.setAtomPalette({-1: ink})
        options.setSymbolColour(ink)
        options.setBackgroundColour((247 / 255, 251 / 255, 249 / 255))
    methyl_labels = 0
    if explicit_methyl:
        for atom in mol.GetAtoms():
            # Only label ordinary terminal CH3; never hide isotope/charge/radical data.
            if (atom.GetAtomicNum() == 6 and not atom.GetIsAromatic()
                    and atom.GetDegree() == 1 and atom.GetTotalNumHs() == 3
                    and atom.GetFormalCharge() == 0 and atom.GetIsotope() == 0
                    and atom.GetNumRadicalElectrons() == 0):
                atom.SetProp("atomLabel", "CH<sub>3</sub>")
                methyl_labels += 1
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    rendered = drawer.GetDrawingText()
    if isinstance(rendered, str):
        output.write_text(rendered, encoding="utf-8")
    else:
        output.write_bytes(rendered)
    result = {"mode": "chemistry", "canonical_smiles": canonical,
              "structure_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
              "width": args.width, "height": args.height,
              "line_width": args.line_width, "font_size": args.font_size,
              "padding": args.padding, "output": str(output),
              "style": style, "explicit_methyl": explicit_methyl,
              "methyl_labels": methyl_labels,
              "source_verified": False,
              "note": "Rendering only; structure fidelity to source requires separate review"}
    metadata.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    for mode in ("original", "enhance"):
        command = modes.add_parser(mode)
        command.add_argument("--input", required=True)
        command.add_argument("--output", required=True)
        if mode == "enhance":
            command.add_argument("--scale", type=int, choices=(1, 2, 3, 4), default=2)
    chemistry = modes.add_parser("chemistry")
    source = chemistry.add_mutually_exclusive_group(required=True)
    source.add_argument("--smiles")
    source.add_argument("--molfile")
    chemistry.add_argument("--output", required=True)
    chemistry.add_argument("--width", type=int, default=600)
    chemistry.add_argument("--height", type=int, default=400)
    chemistry.add_argument("--line-width", type=float, default=2)
    chemistry.add_argument("--font-size", type=int, default=24)
    chemistry.add_argument("--padding", type=float, default=.08)
    chemistry.add_argument("--style", choices=("standard", "memo"), default="standard",
                           help="memo: green ink on pale mint; inspired, not official branding")
    chemistry.add_argument("--explicit-methyl", action="store_true",
                           help="Display ordinary terminal methyl carbons as CH3")
    args = parser.parse_args()
    try:
        result = run(args)
    except (ValueError, OSError, ImportError) as error:
        parser.exit(1, f"Cannot complete {args.mode}: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
