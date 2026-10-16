"""Release integrity and immutable-ID checks at the game/research boundary."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from ai_release import GATES, digest, install, verify


class ReleaseImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)/'game'
        (self.root/'src/core').mkdir(parents=True)
        self.package = Path(self.temporary.name)/'release'
        (self.package/'src/core').mkdir(parents=True)
        (self.package/'src/core/ai.c').write_bytes(b'/* fixture */\n')
        report = json.dumps(dict(schema='feldmarschall-ai-release-qualification-v1',
            candidate='fixture-policy-v1-normal',passed=True,gates=dict.fromkeys(GATES,True))).encode()
        (self.package/'qualification.json').write_bytes(report)
        self.manifest = dict(schema='feldmarschall-ai-release-v1',id='fixture-policy-v1-normal',
            status='qualified',rules='Classic',difficulty='normal',
            information_model='own-army-and-public-observations',
            build_recipe='cc65-banked-inference-v1',target_defines=['BANKED_AI'],
            files={'src/core/ai.c':digest(b'/* fixture */\n')},qualification_sha256=digest(report))
        self.write_manifest()

    def write_manifest(self):
        (self.package/'manifest.json').write_text(json.dumps(self.manifest))

    def test_corrupt_payload_is_rejected_before_changing_game(self):
        (self.root/'src/core/ai.c').write_bytes(b'old game')
        (self.package/'src/core/ai.c').write_bytes(b'corrupt')
        with self.assertRaises(AssertionError): install(self.package,self.root)
        self.assertEqual((self.root/'src/core/ai.c').read_bytes(),b'old game')
        self.assertFalse((self.root/'ai-release').exists())

    def test_existing_identity_cannot_be_redefined(self):
        install(self.package,self.root)
        self.manifest['target_defines'].append('AI_MEMORY')
        self.write_manifest()
        with self.assertRaises(AssertionError): install(self.package,self.root)
        self.assertEqual(verify(self.root)['target_defines'],['BANKED_AI'])

    def test_missing_gate_and_unsafe_path_are_rejected(self):
        original = copy.deepcopy(self.manifest)
        self.manifest['files']={'src/core/../../outside.c':digest(b'anything')}
        self.write_manifest()
        with self.assertRaises(AssertionError): install(self.package,self.root)
        self.manifest=original
        report=json.loads((self.package/'qualification.json').read_text())
        report['gates']['packaging']=False
        encoded=json.dumps(report).encode()
        (self.package/'qualification.json').write_bytes(encoded)
        self.manifest['qualification_sha256']=digest(encoded)
        self.write_manifest()
        with self.assertRaises(AssertionError): install(self.package,self.root)

    def test_installed_source_changes_are_detected(self):
        install(self.package,self.root)
        (self.root/'src/core/ai.c').write_bytes(b'changed after import')
        with self.assertRaises(AssertionError): verify(self.root)


if __name__=='__main__': unittest.main()
