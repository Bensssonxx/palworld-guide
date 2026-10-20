"""Regressions observed during fresh Codex CLI installation trials."""
import sys
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
import json
import tempfile
from copy import deepcopy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'palworld-guide/scripts'))
from task_plan import draft
from workflow import review
from map_preview import checked_svg
from research_bridge import public_text
from research_trace import audit, TraceAuditError
from research_bridge import request


class BetaRegressions(unittest.TestCase):
    def test_base_disclaimer_does_not_change_location_goal(self):
        for question in (
            '给我五个挖金属矿的地点，坐标和地图，并说明有没有把它当成建家推荐。',
            '找三处煤矿地点，不需要建家推荐',
            'Find 5 ore locations, not for building a base',
        ):
            with self.subTest(question=question):
                task = draft(question)
                self.assertEqual(task['steps'][0]['arguments']['purpose'], 'nodes')
        self.assertEqual(draft('找三个适合建家的金属矿地点')['steps'][0]['arguments']['purpose'], 'base-candidates')
        self.assertEqual(draft('找五个金属矿矿群，不用建家')['steps'][0]['arguments']['purpose'], 'clusters')

    def test_actual_chinese_default_disclosure_is_recognized(self):
        run = {'results': {}, 'assumptions': [{'field':'locations.radius','value':40}], 'steps':[]}
        for text in ('默认与限制：半径为 40 游戏坐标单位。', 'Defaults: radius 40 coordinate units.'):
            self.assertEqual(review(run,text)['issues'], [])
        self.assertEqual(review(run,'Here are the results.')['issues'][0]['code'], 'assumptions-not-disclosed')

    def test_preview_rejects_external_or_active_content_before_optional_tools(self):
        start = '<svg xmlns="http://www.w3.org/2000/svg" width="1260" height="960">'
        for content in ('<image href="https://paldb.cc/tile.webp"/>',
                        '<script>alert(1)</script>', '<rect onclick="x()"/>',
                        '<image href="file:///tmp/tile.webp"/>', '<circle cx="0" cy="0"/>'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                checked_svg((start+content+'</svg>').encode())
        with self.assertRaises((ValueError, ET.ParseError)):
            checked_svg(b'<!DOCTYPE svg [<!ENTITY x "x">]><svg/>')

    def test_public_password_topic_is_allowed_but_supplied_secrets_are_not(self):
        for question in ('Does ServerPassword support Xbox and PS5?', 'How do password servers work?', 'What does ServerPassword="" mean?'):
            self.assertEqual(public_text(question), question)
        for question in ('ServerPassword="synthetic-secret"', 'password=synthetic-secret', 'token: synthetic-secret'):
            with self.assertRaises(ValueError):
                public_text(question)

    def test_crossplay_is_research_and_weapon_sources_are_relevant(self):
        task = draft('Can Steam, Xbox and PS5 join one dedicated server?')
        self.assertEqual([step['tool'] for step in task['steps']], ['research'])
        self.assertEqual(task['steps'][0]['arguments']['topic'], 'server')
        task = draft('Palworld Homing Sphere Launcher shots per trigger?')
        step = {'id':'item','tool':'entry','arguments':{'slug':'Homing_Sphere_Launcher','contains':'MagazineSize'}}
        pending = request(task,step)
        self.assertTrue(all('docs.palworldgame.com' not in x['url'] for x in pending['preferred_sources']))
        self.assertFalse(pending['queries'][0].startswith('Palworld Palworld'))

    def test_host_trace_checks_every_query_and_page_open(self):
        url = 'https://docs.palworldgame.com/getting-started/about-server/'
        pending = {'budget': {'searches':3, 'reads':5}}
        packet = {'searches':[{'query':'Palworld server platforms','result_urls':[url]}], 'sources':[{'url':url}]}
        def event(action, snippet):
            return {'type':'item.completed','item':{'type':'web_search','action':action,
                    'results':[{'type':'text_result','url':url,'snippet':snippet}]}}
        search = event({'type':'search','query':'Palworld server platforms'},'A search snippet')
        opened = event({'type':'open_page','url':url},'Total lines: 38')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'host.jsonl'
            def write(events):
                path.write_text(''.join(json.dumps(x)+'\n' for x in events),encoding='utf-8')
            write([search,opened])
            self.assertEqual(audit(packet,pending,path)['status'],'matched')
            batch = event({'type':'other'},'Total lines: 38')
            packet_slash = deepcopy(packet);packet_slash['sources'][0]['url']=url.rstrip('/')
            write([search,batch])
            self.assertEqual(audit(packet_slash,pending,path)['page_reads'],1)
            batch_first_url = deepcopy(opened)
            batch_first_url['item']['results'].append({'type':'text_result','url':url+'extra','snippet':'Total lines: 20'})
            write([search,batch_first_url])
            self.assertEqual(audit(packet,pending,path)['page_reads'],2)
            write([search])
            with self.assertRaisesRegex(TraceAuditError,'page-not-opened'):audit(packet,pending,path)
            changed = deepcopy(packet);changed['searches'][0]['query']='An invented query'
            write([search,opened])
            with self.assertRaisesRegex(TraceAuditError,'query-mismatch'):audit(changed,pending,path)
            write([search,search,opened])
            with self.assertRaisesRegex(TraceAuditError,'query-mismatch'):audit(packet,pending,path)
            write([search]*4+[opened])
            with self.assertRaisesRegex(TraceAuditError,'budget-exceeded'):audit(packet,pending,path)


if __name__ == '__main__':
    unittest.main()
