"""Memo-Canvas local toolchain entrypoint. No implicit model downloads or uploads."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'


def recognition_root():
    config = RUNTIME / 'recognition-runtime.json'
    if not config.exists():
        return RUNTIME
    root = Path(json.loads(config.read_text(encoding='utf-8'))['root'])
    if not root.is_absolute():
        raise ValueError('Shared recognition runtime root must be an absolute path')
    return root


def runtime_python(profile='core'):
    root = RUNTIME if profile == 'core' else recognition_root()
    return root / ('python' if profile == 'core' else profile) / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def command(argv, timeout=180):
    subprocess.run([str(x) for x in argv], check=True, timeout=timeout)


def setup(args):
    uv = shutil.which('uv')
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not uv or not npm:
        raise ValueError('Install uv and Node.js >=20 (including npm) first')
    if args.profile != 'core' and not args.allow_heavy_install:
        raise ValueError('Optional ML dependencies can be large; --allow-heavy-install requires user approval')
    interpreter = runtime_python(args.profile)
    if not interpreter.exists():
        version = args.python or ('3.10' if args.profile == 'molscribe' else sys.executable)
        command([uv, 'venv', '--python', version, interpreter.parent.parent])
    manifest = 'requirements.txt' if args.profile == 'core' else f'{args.profile}.txt'
    command([uv, 'pip', 'install', '--python', interpreter, '-r', ROOT / 'toolchain' / manifest], timeout=1800)
    if args.profile == 'core':
        command([npm, 'ci', '--prefix', ROOT / 'toolchain', '--no-audit', '--no-fund'], timeout=600)
    return {'setup': 'complete', 'profile':args.profile, 'models_installed': False, 'next': 'python scripts/canvas.py doctor'}


def doctor(args):
    modules = {}
    for name in ['PIL', 'rdkit', 'molscribe', 'DECIMER', 'pix2tex']:
        try:
            modules[name] = bool(importlib.util.find_spec(name))
        except (ImportError, ValueError):
            modules[name] = False
    node = shutil.which('node')
    renderers = {'node': 'missing'}
    if node:
        probe = subprocess.run([node, str(ROOT / 'scripts/canvas_render.cjs'), 'doctor'], capture_output=True, text=True, timeout=30)
        renderers = json.loads(probe.stdout) if probe.returncode == 0 else {'error': probe.stderr}
    optional = {}
    for backend, module in [('molscribe','molscribe'),('decimer','DECIMER'),('pix2tex','pix2tex')]:
        interpreter = runtime_python(backend)
        state = {'python':str(interpreter), 'exists':interpreter.is_file(), 'package_present':False}
        if state['exists']:
            probe = subprocess.run([str(interpreter), '-c', 'import importlib.util,sys; print(bool(importlib.util.find_spec(sys.argv[1])))', module], capture_output=True, text=True, timeout=15)
            state['package_present'] = probe.returncode == 0 and probe.stdout.strip() == 'True'
        optional[backend] = state
    record = recognition_root() / 'recognition-validation.json'
    required = list(getattr(args, 'require', []) or [])
    table = None
    if 'table' in required:
        table = {'ok': False, 'error': 'node missing'}
        if node:
            probe = subprocess.run([node, str(ROOT / 'scripts/render_table.cjs'), '--doctor'],
                                   capture_output=True, text=True, timeout=30)
            table = json.loads(probe.stdout) if probe.returncode == 0 else {
                'ok': False, 'error': (probe.stderr or probe.stdout).strip()[:500]}
            table['ok'] = probe.returncode == 0
    checks = {
        'rdkit': modules['rdkit'],
        'chemistry': modules['rdkit'],
        'molscribe': optional['molscribe']['package_present'] or modules['molscribe'],
        'decimer': optional['decimer']['package_present'] or modules['DECIMER'],
        'pix2tex': optional['pix2tex']['package_present'] or modules['pix2tex'],
        'table': bool(table and table.get('ok')),
    }
    missing = [name for name in required if not checks.get(name, False)]
    if missing:
        raise ValueError('required toolchain not loaded: ' + ', '.join(missing)
                         + '; install/activate the isolated runtime and rerun doctor')
    return {'python':sys.executable, 'modules_present_not_inference_verified':modules,
            'required': required, 'requirements_ok': not missing,
            'table_renderer':table,
            'optional_environments':optional,
            'recognition_runtime_root':str(recognition_root()),
            'local_molscribe_checkpoint':str(recognition_root() / 'models/molscribe-swin-base-1m.pth') if (recognition_root() / 'models/molscribe-swin-base-1m.pth').is_file() else 'not_downloaded',
            'recorded_validation':json.loads(record.read_text(encoding='utf-8')) if record.exists() else None,
            'renderers':renderers, 'recognition_status':'models_not_loaded_by_doctor; recorded validation is historical, not a fresh accuracy guarantee',
            'setup_command':'python scripts/canvas.py setup', 'network_used':False}


def recognize(args):
    source = Path(args.input).resolve(strict=True)
    output = Path(args.output).resolve()
    if output.exists():
        raise ValueError(f'Refusing to overwrite: {output}')
    if source.stat().st_size > 30_000_000:
        raise ValueError('Input image exceeds 30 MB')
    # Fail before importing libraries that may download at import/initialization time.
    if args.backend == 'molscribe':
        if not args.checkpoint or not Path(args.checkpoint).is_file():
            raise ValueError('MolScribe requires --checkpoint pointing to trusted local weights')
        import torch
        from molscribe import MolScribe
        import numpy as np
        from PIL import Image, ImageOps
        model = MolScribe(str(Path(args.checkpoint).resolve()), device=torch.device('cpu'))
        # Upstream cv2.imread cannot reliably read Windows Unicode paths.
        # Decode with Pillow and use the upstream RGB-array interface instead.
        with Image.open(source) as image:
            if image.width * image.height > 40_000_000 or getattr(image,'n_frames',1) != 1:
                raise ValueError('Expected a single image up to 40 MP')
            pixels = np.asarray(ImageOps.exif_transpose(image).convert('RGB'))
        raw = model.predict_image(pixels, return_atoms_bonds=True, return_confidence=True)
    elif args.backend == 'decimer':
        if not args.allow_model_download:
            raise ValueError('DECIMER may download at import/first use; explicit --allow-model-download required after user approval')
        from DECIMER import predict_SMILES
        raw = {'smiles':predict_SMILES(str(source))}
    else:
        if not args.allow_model_download:
            raise ValueError('pix2tex may download weights; explicit --allow-model-download required after user approval')
        from PIL import Image
        from pix2tex import cli
        from unittest.mock import patch
        LatexOCR = cli.LatexOCR
        model = LatexOCR()
        with Image.open(source) as image:
            if image.width * image.height > 40_000_000:
                raise ValueError('Image exceeds 40 MP')
            # Upstream copies predictions to the clipboard by default; keep this adapter file-only.
            with patch.object(cli.clipboard, 'copy', lambda value: None):
                raw = {'latex':model(image.copy())}
    key = 'latex' if args.backend == 'pix2tex' else 'smiles'
    if not isinstance(raw, dict) or not isinstance(raw.get(key), str) or not raw[key].strip():
        raise ValueError('Recognizer returned no usable structure; preserve original and review')
    result = {'backend':args.backend, 'input':str(source), 'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'raw':raw, 'source_verified':False, 'status':'candidate_requires_review'}
    if args.checkpoint:
        result['checkpoint_sha256'] = hashlib.sha256(Path(args.checkpoint).read_bytes()).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Convert numpy scalar/array results without discarding fields.
    def convert(value):
        if hasattr(value, 'tolist'):
            return value.tolist()
        raise TypeError(f'Non-JSON recognition field: {type(value).__name__}')
    encoded = json.dumps(result, ensure_ascii=False, indent=2, default=convert)
    with output.open('x', encoding='utf-8') as stream:
        stream.write(encoded)
    return {'output':str(output), 'status':result['status'], 'source_verified':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    p = modes.add_parser('setup')
    p.add_argument('--profile', choices=['core','molscribe','decimer','pix2tex'], default='core')
    p.add_argument('--allow-heavy-install', action='store_true')
    p.add_argument('--python', help='Python version/path for a new environment; MolScribe defaults to 3.10')
    doctor_parser = modes.add_parser('doctor')
    doctor_parser.add_argument('--require', action='append',
                               choices=['rdkit', 'chemistry', 'molscribe', 'decimer', 'pix2tex', 'table'],
                               default=[])
    for mode in ['formula', 'svg', 'flowchart']:
        p = modes.add_parser(mode)
        p.add_argument('--input', required=True)
        p.add_argument('--output', required=True)
        p.add_argument('--font-size', type=int, default=32)
    p = modes.add_parser('recognize')
    p.add_argument('--backend', choices=['molscribe', 'decimer', 'pix2tex'], required=True)
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--checkpoint')
    p.add_argument('--allow-model-download', action='store_true')
    args, extra = parser.parse_known_args()
    if extra:
        parser.error('Unknown arguments: ' + ' '.join(extra))
    # Reuse the selected isolated runtime, including --backend=NAME syntax.
    profile = args.backend if args.mode == 'recognize' else 'core'
    isolated = runtime_python(profile)
    if isolated.exists() and Path(sys.executable).resolve() != isolated.resolve() and args.mode != 'setup':
        return subprocess.call([str(isolated), str(Path(__file__).resolve()), *sys.argv[1:]])
    if args.mode == 'recognize':
        os.environ.setdefault('NO_ALBUMENTATIONS_UPDATE','1')
        os.environ.setdefault('PYSTOW_HOME', str(recognition_root() / 'models/decimer-cache'))
        if args.backend == 'molscribe' and not args.checkpoint:
            args.checkpoint = str(recognition_root() / 'models/molscribe-swin-base-1m.pth')
    try:
        if args.mode in ['formula', 'svg', 'flowchart']:
            node = shutil.which('node')
            if not node:
                raise ValueError('Node.js >=20 required; run setup first')
            command([node, ROOT / 'scripts/canvas_render.cjs', args.mode, args.input, args.output, args.font_size])
            return 0
        result = {'setup':setup, 'doctor':doctor, 'recognize':recognize}[args.mode](args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, ImportError, subprocess.SubprocessError, RuntimeError) as error:
        print(f'Cannot complete {args.mode}: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
