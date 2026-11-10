"""Adapter contract tests; mocks do NOT validate model inference accuracy."""
import argparse
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import canvas


class Adapters(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.image = self.root / 'scan.png'
        self.image.write_bytes(b'mock image - not a real scan')

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, backend, **kw):
        return argparse.Namespace(input=str(self.image), output=str(self.root / 'candidate.json'),
                                  backend=backend, checkpoint=kw.get('checkpoint'),
                                  allow_model_download=kw.get('allow_model_download', False))

    def test_decimer_requires_consent(self):
        with self.assertRaisesRegex(ValueError, 'allow-model-download'):
            canvas.recognize(self.args('decimer'))

    def test_pix2tex_requires_consent(self):
        with self.assertRaisesRegex(ValueError, 'allow-model-download'):
            canvas.recognize(self.args('pix2tex'))

    def test_molscribe_requires_checkpoint(self):
        with self.assertRaisesRegex(ValueError, 'checkpoint'):
            canvas.recognize(self.args('molscribe'))

    def test_no_overwrite(self):
        args=self.args('decimer')
        Path(args.output).write_text('keep')
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            canvas.recognize(args)
        self.assertEqual(Path(args.output).read_text(),'keep')

    def test_decimer_contract_only(self):
        fake=types.SimpleNamespace(predict_SMILES=lambda filename:'CCO')
        with patch.dict('sys.modules', {'DECIMER':fake}):
            result=canvas.recognize(self.args('decimer',allow_model_download=True))
        data=json.loads(Path(result['output']).read_text(encoding='utf-8'))
        self.assertEqual(data['raw']['smiles'],'CCO')
        self.assertFalse(data['source_verified'])
        self.assertEqual(data['status'],'candidate_requires_review')

    def test_empty_candidate_is_not_success(self):
        with patch.dict('sys.modules', {'DECIMER':types.SimpleNamespace(predict_SMILES=lambda filename:'')}):
            with self.assertRaisesRegex(ValueError, 'no usable structure'):
                canvas.recognize(self.args('decimer',allow_model_download=True))

    def test_molscribe_contract_only(self):
        from PIL import Image
        # Import before patch.dict restores sys.modules: NumPy's C extension
        # cannot be safely unloaded/reimported by a later RDKit test.
        import numpy
        Image.new('RGB',(40,20),'white').save(self.image)
        checkpoint=self.root/'trusted.pth'
        checkpoint.write_bytes(b'mock weights, not a real model')
        seen={}
        class Model:
            def __init__(self,path,device):
                seen.update(path=path,device=device)
            def predict_image(self,image,**kwargs):
                seen['image_shape']=image.shape
                seen.update(kwargs)
                return {'smiles':'CCO','molfile':'mock molfile','confidence':0.5}
        with patch.dict('sys.modules',{'molscribe':types.SimpleNamespace(MolScribe=Model),'torch':types.SimpleNamespace(device=lambda x:x)}):
            result=canvas.recognize(self.args('molscribe',checkpoint=str(checkpoint)))
        self.assertTrue(seen['return_atoms_bonds'])
        self.assertTrue(seen['return_confidence'])
        self.assertEqual(seen['device'],'cpu')
        self.assertEqual(seen['image_shape'],(20,40,3))
        data=json.loads(Path(result['output']).read_text(encoding='utf-8'))
        self.assertEqual(data['raw']['molfile'],'mock molfile')
        self.assertIn('checkpoint_sha256',data)

    def test_pix2tex_contract_disables_clipboard(self):
        from PIL import Image
        Image.new('RGB',(40,20),'white').save(self.image)
        clipboard=types.SimpleNamespace(copy=lambda value:self.fail('clipboard must not change'))
        class Model:
            def __call__(self,image):
                clipboard.copy('x=1')
                return 'x=1'
        cli=types.SimpleNamespace(LatexOCR=Model,clipboard=clipboard)
        with patch.dict('sys.modules',{'pix2tex':types.SimpleNamespace(cli=cli)}):
            result=canvas.recognize(self.args('pix2tex',allow_model_download=True))
        data=json.loads(Path(result['output']).read_text(encoding='utf-8'))
        self.assertEqual(data['raw']['latex'],'x=1')

    def test_shared_runtime_leaves_core_environment_local(self):
        runtime=self.root/'local-runtime'
        runtime.mkdir()
        shared=self.root/'shared-runtime'
        (runtime/'recognition-runtime.json').write_text(json.dumps({'root':str(shared)}),encoding='utf-8')
        with patch.object(canvas,'RUNTIME',runtime):
            self.assertIn(shared,canvas.runtime_python('molscribe').parents)
            self.assertIn(runtime,canvas.runtime_python('core').parents)

    def test_shared_runtime_rejects_relative_path(self):
        runtime=self.root/'local-runtime'
        runtime.mkdir()
        (runtime/'recognition-runtime.json').write_text('{"root":"relative"}',encoding='utf-8')
        with patch.object(canvas,'RUNTIME',runtime):
            with self.assertRaisesRegex(ValueError,'absolute'):
                canvas.recognition_root()


if __name__ == '__main__':
    unittest.main(verbosity=2)
