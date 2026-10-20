import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'palworld-guide/scripts'))
sys.path.insert(0,str(ROOT/'tools'))
from workflow import execute
from provider_api import material_deficits
from install import install


class PublicCandidateTests(unittest.TestCase):
    def test_owned_species_work_without_private_workspace(self):
        task=json.loads((ROOT/'examples/breeding-task.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as tmp:
            r=execute(task,Path(tmp)/'run',offline=True,cache_dir=str(Path(tmp)/'empty-cache'))
        self.assertEqual(r['results']['breed']['data']['target']['name'],'Pyrin')
        self.assertEqual(r['execution_status'],'completed')

    def test_synthetic_recipe_arithmetic_and_source_conflict(self):
        bundle={'cross_check':{'status':'agreed','recipe':{'technology_level':1},'retrieval':{'url':'https://paldb.cc/en/Example'}},
                'item':{'id':'synthetic','name':'Synthetic'},'materials':[{'id':'stone','name':'Stone','count':5}],
                'yields':10,'api_evidence':[]}
        r=material_deficits(bundle,11,{'Stone':2})
        self.assertEqual(r['batches'],2);self.assertEqual(r['materials'][0]['missing'],8)
        bundle['cross_check']['status']='conflict'
        self.assertEqual(material_deficits(bundle,11)['status'],'recipe-evidence-incomplete')

    def test_install_is_explicit_local_and_preserves_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=install(tmp)
            self.assertTrue((target/'SKILL.md').exists());self.assertTrue((target/'LICENSE').exists())
            with self.assertRaises(ValueError):install(tmp)

    def test_unlicensed_bulk_snapshots_are_not_distributed(self):
        refs=ROOT/'palworld-guide/references'
        self.assertFalse((refs/'demo-maps.json').exists())
        self.assertFalse((refs/'demo-comparisons.json').exists())
        self.assertEqual(json.loads((refs/'integration-examples.json').read_text(encoding='utf-8'))['recipes'],[])


if __name__=='__main__':unittest.main()
