import copy
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'palworld-guide/scripts'))
from workflow import execute, envelope
from research_bridge import request, validate_packet
from task_plan import draft


def packet(pending, action='answer'):
    now=datetime.now(timezone.utc).isoformat();url='https://docs.palworldgame.com/settings-and-operation/mod/'
    excerpt='Synthetic test excerpt; not a gameplay claim.'
    return {'schema':1,'request_id':pending['id'],
            'searches':[{'query':'Palworld server mods','provider':'synthetic-test-provider','searched_at':now,'result_urls':[url]}],
            'sources':[{'id':'official','url':url,'discovered_from':url,'title':'Synthetic source fixture','role':'official',
                        'retrieved_at':now,'read_status':'read','excerpt':excerpt,'excerpt_sha256':hashlib.sha256(excerpt.encode()).hexdigest()}],
            'findings':[{'claim':'Synthetic finding for validation only.','source_ids':['official']}],
            'resolution':{'action':action,'limitations':[]}}


class ResearchTests(unittest.TestCase):
    def test_rejected_receipt_preserves_safe_specific_diagnosis(self):
        task=draft('Explain a new Palworld mechanic')
        with tempfile.TemporaryDirectory() as temp:
            first=execute(task,Path(temp)/'first');pending=first['research_queue'][0]
            receipt=packet(pending);receipt['sources'][0]['discovered_from']='https://unseen.example/a'
            resumed=execute(task,Path(temp)/'resumed',research={pending['id']:receipt},previous=first)
        self.assertIn('Page must trace to an actual search result',resumed['results']['s1']['gaps'][0])
        self.assertNotIn('unseen.example',resumed['results']['s1']['gaps'][0])

    def test_failed_map_fetch_also_requests_public_evidence(self):
        t=draft('Find a sourced map for coal')
        t['steps']=[{'id':'map','tool':'map','arguments':{'points':{}}}]
        with tempfile.TemporaryDirectory() as temp, patch('workflow.call_tool',return_value=envelope('map',status='failed',gaps=['Public tile unavailable'])):
            r=execute(t,Path(temp)/'run')
        self.assertEqual(r['results']['map']['status'],'awaiting-research')
        self.assertEqual(r['research_queue'][0]['original_tool'],'map')

    def test_unknown_request_yields_real_host_handoff(self):
        t=draft('How does this new Palworld weapon mechanic work?')
        with tempfile.TemporaryDirectory() as temp:
            r=execute(t,Path(temp)/'initial')
            self.assertEqual(r['execution_status'],'awaiting-research')
            self.assertEqual(len(r['research_queue']),1)
            self.assertTrue((Path(temp)/'initial/research-queue.json').exists())
            self.assertFalse(r['results']['s1']['evidence'])

    def test_receipt_resumes_and_binds_into_next_tool(self):
        t=draft('Research a new mechanic')
        t['steps'].append({'id':'followup','tool':'sources','arguments':{},'depends_on':['s1'],
                           'bindings':{'question':{'step':'s1','path':['findings',0,'claim']}}})
        with tempfile.TemporaryDirectory() as temp:
            a=execute(t,Path(temp)/'a');pending=a['research_queue'][0]
            self.assertEqual(a['results']['followup']['status'],'blocked')
            b=execute(t,Path(temp)/'b',research={pending['id']:packet(pending)},previous=a)
            self.assertEqual(b['results']['s1']['status'],'completed')
            self.assertIn('https://docs.palworldgame.com/settings-and-operation/mod/',[e['url'] for e in b['results']['s1']['evidence']])
            self.assertEqual(b['results']['followup']['data']['status'],'source-selection-not-an-answer')
            self.assertFalse(b['research_queue'])

    def test_article_retry_is_bounded_and_preserves_attempt(self):
        t=draft('A new mechanic');t['steps']=[{'id':'entry','tool':'entry','arguments':{'slug':'Pyrin','contains':'missing'}}]
        with tempfile.TemporaryDirectory() as temp, patch('workflow.call_tool',side_effect=[envelope('entry',{'matched':False},'partial',['No match']),envelope('entry',{'matched':True})]) as call:
            a=execute(t,Path(temp)/'a');p=a['research_queue'][0];receipt=packet(p,'retry')
            receipt['resolution']['arguments']={'slug':'Pyrin','contains':'Map'}
            b=execute(t,Path(temp)/'b',research={p['id']:receipt},previous=a)
            self.assertEqual(b['results']['entry']['status'],'completed')
            self.assertFalse(b['results']['entry']['original_result']['data']['matched'])
            self.assertEqual(call.call_count,2)
            execute(t,Path(temp)/'c',research={p['id']:receipt},previous=b)
            self.assertEqual(call.call_count,2)

    def test_missing_player_position_does_not_search(self):
        with tempfile.TemporaryDirectory() as temp:
            r=execute(draft('找我附近五个煤矿地点'),Path(temp)/'a')
        self.assertEqual(r['execution_status'],'blocked');self.assertFalse(r['research_queue'])

    def test_explicit_offline_never_queues_online_search(self):
        with tempfile.TemporaryDirectory() as temp:
            r=execute(draft('A new mechanic'),Path(temp)/'a',offline=True)
        self.assertFalse(r['research_queue']);self.assertEqual(r['execution_status'],'blocked')

    def test_private_question_is_not_exported_as_search(self):
        with tempfile.TemporaryDirectory() as temp:
            r=execute(draft('Explain setting password=synthetic-secret at /Users/private/config'),Path(temp)/'a')
        self.assertFalse(r['research_queue'])
        self.assertFalse(any(x.get('research_request') for x in r['results'].values()))

    def test_packet_cannot_be_reused_for_different_task(self):
        t=draft('A new mechanic');u=draft('Another mechanic')
        with tempfile.TemporaryDirectory() as temp:
            a=execute(t,Path(temp)/'a')
            with self.assertRaises(ValueError):execute(u,Path(temp)/'b',previous=a)

    def test_source_records_need_read_hash_identity_and_citations(self):
        p=request(draft('A new mechanic'),{'id':'s1','tool':'research','arguments':{}})
        changes=[lambda x:x.update(request_id='wrong'),
                 lambda x:x['sources'][0].update(read_status='snippet-only'),
                 lambda x:x['sources'][0].update(excerpt_sha256='wrong'),
                 lambda x:x['findings'][0].update(source_ids=['missing']),
                 lambda x:x['sources'][0].update(url='https://127.0.0.1/a'),
                 lambda x:x['sources'][0].update(discovered_from='https://unseen.example/a')]
        for change in changes:
            x=packet(p);change(x)
            with self.subTest(receipt=x),self.assertRaises(ValueError):validate_packet(x,p)

    def test_no_search_results_is_unresolved_not_an_answer(self):
        p=request(draft('A new mechanic'),{'id':'s1','tool':'research','arguments':{}});x=packet(p)
        x['searches'][0]['result_urls']=[];x['sources']=[];x['findings']=[]
        with self.assertRaises(ValueError):validate_packet(x,p)
        x['resolution']={'action':'unresolved','limitations':['No search results were found']}
        self.assertEqual(validate_packet(x,p)['resolution']['action'],'unresolved')

    def test_research_retry_cannot_read_local_files(self):
        p=request(draft('A new mechanic'),{'id':'s1','tool':'entry','arguments':{}});x=packet(p,'retry')
        x['resolution']['arguments']={'files':{'manifest':'/Users/private/Info.json'}}
        with self.assertRaises(ValueError):validate_packet(x,p)

    def test_failed_packet_does_not_unlock_dependencies(self):
        t=draft('A new mechanic');t['steps'].append({'id':'b','tool':'odds','arguments':{'percent':3,'runs':2},'depends_on':['s1']})
        with tempfile.TemporaryDirectory() as temp:
            a=execute(t,Path(temp)/'a');p=a['research_queue'][0]
            b=execute(t,Path(temp)/'b',research={p['id']:{'schema':1,'request_id':'wrong'}},previous=a)
        self.assertEqual(b['results']['s1']['status'],'blocked');self.assertEqual(b['results']['b']['status'],'blocked')


if __name__=='__main__':unittest.main()
