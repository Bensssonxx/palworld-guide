import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

SCRIPTS=Path(__file__).resolve().parents[1]/'palworld-guide/scripts'
sys.path.insert(0,str(SCRIPTS))
import public_sources as sources
import map_tools as maps
import server_check as server


class SourceTests(unittest.TestCase):
    def test_only_curated_https_hosts(self):
        for url in ['file:///tmp/game','http://paldb.cc/','https://paldb.cc.evil.test/',
                    'https://user:secret@paldb.cc/','https://127.0.0.1/','https://paldb.cc:444/']:
            with self.assertRaises(ValueError): sources.check_url(url)
        self.assertEqual(sources.check_url('https://paldb.cc/en/Mining'),'https://paldb.cc/en/Mining')

    def test_text_reader_ignores_script_and_preserves_table(self):
        p=sources.PageText();p.feed('<script>ignore()</script><table><tr><td>A</td><td>B</td></tr></table>')
        text='\n'.join(p.lines())
        self.assertNotIn('ignore',text);self.assertIn('A | B',text)

    def test_sources_rank_official_and_provider_roles(self):
        r=sources.select_sources('mods','模组不出现')
        self.assertEqual(r['sources'][0]['priority'],10)
        self.assertTrue(all('mods' in x['topics'] for x in r['sources']))

    def test_offline_cache_verifies_hash(self):
        url='https://paldb.cc/en/Mining';key=hashlib.sha256(url.encode()).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);b=b'public sample'
            (path/f'{key}.bin').write_bytes(b)
            (path/f'{key}.json').write_text(json.dumps({'url':url,'fetched_at':'2026-10-19','sha256':hashlib.sha256(b).hexdigest()}))
            body,info=sources.get_public(url,temp,offline=True)
            self.assertEqual(body,b);self.assertTrue(info['cache'])
            (path/f'{key}.bin').write_bytes(b'changed')
            with self.assertRaises(ValueError):sources.get_public(url,temp,offline=True)


class MapTests(unittest.TestCase):
    def test_data_json_literal_not_javascript_execution(self):
        text='var config={"answer":42}; throw new Error("must not execute");'
        self.assertEqual(maps.json_assignment(text,'config'),{'answer':42})

    def test_known_source_anchor_axis_and_precision(self):
        x,y=maps.raw_to_game({'X':-528455,'Y':-512500})
        self.assertAlmostEqual(x,-1460.7843137254902)
        self.assertAlmostEqual(y,-881.4095860566449)

    def test_map_corners_match_provider_orientation(self):
        xmin,xmax,ymin,ymax=maps.world_bounds()
        self.assertEqual(maps.game_to_normal(xmin,ymax),(0,0))
        self.assertEqual(maps.game_to_normal(xmax,ymin),(1,1))

    def test_reject_changed_bounds(self):
        config={'landScapeRealPositionMin':{'X':0,'Y':0},'landScapeRealPositionMax':{'X':1,'Y':1}}
        with self.assertRaises(ValueError):maps.validate_config(config)

    def test_reject_wrong_map_unknown_source_and_nonfinite(self):
        good={'map_id':'palpagos-main','points':[{'label':'p','x':0,'y':0,'source_url':'https://paldb.cc/'}]}
        for payload in [good|{'map_id':'world-tree'},good|{'points':[{'label':'p','x':0,'y':0}]},
                        good|{'points':[{'label':'p','x':math.nan,'y':0,'source_url':'https://paldb.cc/'}]}]:
            with self.assertRaises(ValueError):maps.checked_points(payload)

    def test_rendered_marker_stays_on_projection_and_escapes_label(self):
        payload={'map_id':'palpagos-main','points':[{'label':'<script>bad</script>','x':0,'y':0,'status':'user-provided','source_url':'https://paldb.cc/'}]}
        svg,evidence=maps.render_svg(payload)
        tree=ET.fromstring(svg)
        self.assertNotIn('<script>',svg)
        marker=tree.find('.//{http://www.w3.org/2000/svg}circle')
        self.assertAlmostEqual(float(marker.attrib['cx']),415)
        self.assertAlmostEqual(float(marker.attrib['cy']),490)
        self.assertFalse(evidence['embedded_tiles'])

    def test_fast_travel_sort_and_cluster_spacing(self):
        records=[{'type':'Coal','item':'coal','ipos':{'X':100,'Y':100}},
                 {'type':'Coal','item':'coal','ipos':{'X':101,'Y':100}},
                 {'type':'Coal','item':'coal','ipos':{'X':300,'Y':100}},
                 {'type':'Fast Travel','item':'travel','ipos':{'X':300,'Y':101}}]
        with patch.object(maps,'load_dataset',return_value=(records,{'url':maps.MAP_DATA_URL,'sha256':'sample'})):
            result=maps.locate('coal','Coal',2,sort='fast-travel',min_separation=80)
        self.assertEqual(result['points'][0]['x'],300)
        self.assertEqual(len(result['points']),2)

    def test_chinese_map_and_nearby_travel_keep_source_geometry(self):
        point={'label':'Coal','x':0,'y':0,'source_url':'https://paldb.cc/en/Palpagos_Islands','status':'source-record',
               'nearest_fast_travel':{'label':'Anubis Dunes','x':2,'y':3,'source_url':'https://paldb.cc/en/Palpagos_Islands','distance_coordinate_units':math.sqrt(13)}}
        payload={'map_id':'palpagos-main','points':[point]}
        svg,ev=maps.render_svg(payload,language='zh',show_fast_travel=True)
        self.assertIn('煤炭',svg);self.assertIn('传送点',svg);self.assertNotIn('Anubis Dunes',svg);self.assertIn('T1',svg)
        self.assertEqual(ev['fast_travel_markers'][0]['label'],'Anubis Dunes') # Canonical source identity stays in evidence.
        self.assertNotIn('Public source record',svg);self.assertNotIn('Palworld location map',svg)
        self.assertEqual((ev['markers'][0]['x'],ev['markers'][0]['y']),(0,0))
        self.assertEqual((ev['fast_travel_markers'][0]['x'],ev['fast_travel_markers'][0]['y']),(2,3))
        self.assertLess(svg.index('T1</text>'),svg.index('<circle'))
        self.assertEqual(len(ET.fromstring(svg).findall('.//{http://www.w3.org/2000/svg}circle')),1)

    def test_fast_travel_option_validates_its_own_coordinates(self):
        payload={'map_id':'palpagos-main','points':[{'label':'Coal','x':0,'y':0,'source_url':'https://paldb.cc/',
                 'nearest_fast_travel':{'label':'Bad','x':math.nan,'y':3,'source_url':'https://paldb.cc/'}}]}
        with self.assertRaises(ValueError):maps.render_svg(payload,show_fast_travel=True)
        with self.assertRaises(ValueError):maps.render_svg(payload,language='fr')


class ServerTests(unittest.TestCase):
    def test_password_ip_and_quoted_comma_not_echoed(self):
        world='[/Script/Pal.PalGameWorldSettings]\nOptionSettings=(AdminPassword="secret,with,commas",ServerPassword="othersecret",PublicIP="10.20.30.40",ServerPlayerMaxNum=12,PalStomachDecreaceRate=1.0)'
        report=server.inspect_server(world_text=world)
        text=json.dumps(report)
        self.assertNotIn('secret',text);self.assertNotIn('10.20.30.40',text)
        self.assertEqual(report['recognized_gameplay_settings']['ServerPlayerMaxNum'],12)

    def test_repeated_active_mods_and_server_rules(self):
        manifest={'PackageName':'DemoPal','Dependencies':['PalSchema'],'MinRevision':100,'InstallRule':[{'Type':'PalSchema','IsServer':True}]}
        config='[PalModSettings]\nbGlobalEnableMod=True\nActiveModList=DemoPal\nActiveModList=PalSchema'
        report=server.inspect_server(mod_text=config,manifest=manifest,os_name='windows',revision=101)
        self.assertEqual(report['manifest']['server_rule_count'],1)
        self.assertIn('PalSchema',report['manifest']['active_mods'])
        self.assertNotIn('package-not-active',[f['code'] for f in report['findings']])

    def test_disabled_unsupported_and_missing_dependency(self):
        manifest={'PackageName':'DemoPal','Dependencies':['PalSchema'],'InstallRule':[{'Type':'Lua','IsServer':True}]}
        report=server.inspect_server(mod_text='bGlobalEnableMod=False\nActiveModList=UE4SS',manifest=manifest,os_name='linux')
        codes={f['code'] for f in report['findings']}
        self.assertTrue({'mods-disabled','package-not-active','dependencies-not-listed','documented-os'}<=codes)

    def test_client_only_rule_is_not_server_compatibility(self):
        report=server.inspect_server(manifest={'PackageName':'DemoPal','InstallRule':[{'Type':'Lua'}]})
        self.assertIn('no-server-rule',[x['code'] for x in report['findings']])

    def test_log_signals_are_not_raw_logs_or_diagnosed_cause(self):
        report=server.inspect_server(log_text='Private user/path token=secret\nUE4SS Git SHA: 2281fa31\nAccess violation')
        self.assertNotIn('secret',json.dumps(report))
        self.assertEqual(report['log_signals']['loader_git_hashes'],['2281fa31'])
        self.assertEqual(report['log_signals']['failure_signal_count'],1)

    def test_malformed_or_path_packages_rejected(self):
        for manifest in [{'PackageName':'../evil'},{'PackageName':'DemoPal','Dependencies':'UE4SS'}]:
            with self.assertRaises(ValueError):server.inspect_server(manifest=manifest)
        with self.assertRaises(ValueError):server.parse_settings('OptionSettings=(AdminPassword="unfinished)')

    def test_food_diagnosis_depends_on_observation(self):
        empty=server.inspect_server(food='empty');present=server.inspect_server(food='available')
        self.assertEqual(empty['findings'][0]['code'],'empty-feedbox')
        self.assertEqual(present['findings'][0]['code'],'food-present')

    def test_revision_is_separate_from_version(self):
        manifest={'PackageName':'DemoPal','MinRevision':100,'InstallRule':[]}
        result=server.inspect_server(manifest=manifest,revision=99)
        self.assertIn('revision-too-old',[f['code'] for f in result['findings']])

    def test_invalid_mod_switch_has_actionable_finding(self):
        result=server.inspect_server(mod_text='bGlobalEnableMod=Maybe')
        self.assertIn('invalid-mod-switch',[f['code'] for f in result['findings']])

    def test_server_install_rule_does_not_coerce_invalid_boolean(self):
        for value in ('true',1,None):
            with self.assertRaises(ValueError):
                server.inspect_server(manifest={'PackageName':'DemoPal','InstallRule':[{'Type':'Lua','IsServer':value}]})


if __name__=='__main__':unittest.main()
