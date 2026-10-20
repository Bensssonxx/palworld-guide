import sys,unittest,json,math
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'palworld-guide/scripts'))
import pal_compare as pals
import farm_plan as farm

HEADER='<h5 class="card-header">Ground Mounts /3</h5><table><tr><th>name<th>Run Speed<th>Ride Sprint Speed<th>Tech Level<th>Stamina<th>GravityScale<th>JumpZVelocity'
HTML=HEADER+'<tr><td><a href="Fenglope">Fenglope</a><td>750<td>1050<td>26<td>140<td>2<td>1300<tr><td><a href="Pyrin">Pyrin</a><td>850<td>1300<td>29<td>100<td>3<td>1500<tr><td><a href="Paladius">Paladius</a><td>800<td>1800<td>61<td>400<td>2.5<td>1000</table>'
META={'url':'https://paldb.cc/en/Mounts','sha256':'synthetic','fetched_at':'2026-10-19T00:00:00Z'}
class CompareTests(unittest.TestCase):
 def test_optional_html_closures_and_stat_columns(self):
  rows=pals.parse_table(HTML,'ground');self.assertEqual(len(rows),3);self.assertEqual(rows[0]['ride_sprint_speed'],1050);self.assertEqual(rows[0]['stamina'],140);self.assertEqual(rows[0]['source_url'],'https://paldb.cc/en/Fenglope')
 def test_technology_filter_tradeoffs_and_baseline(self):
  with patch.object(pals,'get_public',return_value=(HTML.encode(),META)):
   r=pals.compare(level=52,baseline='Fenglope',limit=1)
  self.assertEqual(r['matching_records'],2);self.assertEqual(r['records'][0]['name'],'Pyrin');self.assertTrue(r['records'][0]['pareto_frontier']);self.assertEqual(r['records'][0]['delta_from_baseline']['stamina'],-40)
 def test_changed_heading_and_flying_section_rejected(self):
  for html in [HTML.replace('Ride Sprint Speed','Speed'),HTML.replace('Ground Mounts','Flying Mounts')]:
   with self.assertRaises(ValueError):pals.parse_table(html,'ground')
 def test_work_columns_are_separate(self):
  rows=pals.parse_table('<table><tr><th>Pal<th>Level<th>4 Level<tr><td><a href="Dumud">Dumud</a><td>2<td>3</table>','mining');self.assertEqual(rows[0]['listed_work_level'],2);self.assertEqual(rows[0]['four_star_work_level'],3)
 def test_unknown_entities_not_silently_dropped(self):
  with patch.object(pals,'get_public',return_value=(HTML.encode(),META)):
   with self.assertRaises(ValueError):pals.compare(names=['Invented Pal'])
 def test_missing_numeric_values_and_unsafe_entry(self):
  with self.assertRaises(ValueError):pals.parse_table(HTML.replace('<td>1050','<td>NaN'),'ground')
  with self.assertRaises(ValueError):pals.entry('../private')
 def test_navigation_is_not_article_evidence(self):
  body=b'<header>Ammo</header><nav><div>Ammo</div></nav><main><h2>Partner Skill</h2><p>Can double jump while mounted.</p></main><footer>Ammo</footer>'
  with patch.object(pals,'get_public',return_value=(body,META)):
   absent=pals.entry('Fenglope','Ammo');present=pals.entry('Fenglope','Partner Skill')
  self.assertFalse(absent['matched']);self.assertEqual(absent['excerpt'],'');self.assertTrue(present['matched']);self.assertIn('double jump',present['excerpt'])
 def test_work_table_does_not_claim_capture_level(self):
  with self.assertRaises(ValueError):pals.compare('mining',level=35)
 def test_article_links_include_actual_map_queries_and_exclude_navigation(self):
  body=b'<nav><a href="Wrong">Map</a></nav><main><h5>Map</h5><a href="Palpagos_Islands?pal=FireKirin&amp;t=dayTimeLocations">Day (95)</a><a href="javascript:bad()">Bad</a></main>'
  with patch.object(pals,'get_public',return_value=(body,META)):r=pals.entry('Pyrin','Map')
  self.assertTrue(r['matched']);self.assertEqual(len(r['article_links']),1)
  self.assertEqual(r['article_links'][0]['url'],'https://paldb.cc/en/Palpagos_Islands?pal=FireKirin&t=dayTimeLocations')
  self.assertEqual(r['article_links'][0]['section'],'Map')
 def test_unmatched_article_does_not_return_unrelated_links(self):
  with patch.object(pals,'get_public',return_value=(b'<main><h5>Map</h5><a href="Mining">Mining</a></main>',META)):r=pals.entry('Pyrin','Ammo')
  self.assertFalse(r['matched']);self.assertEqual(r['article_links'],[])
  self.assertEqual(r['available_sections'],['Map'])
  self.assertEqual(r['overview_links'][0]['url'],'https://paldb.cc/en/Mining')
  self.assertIn('Map',r['overview_excerpt'])

STAGES=[{'label':'A','conditional_percent':50,'minutes':8,'source_url':'https://example.com/a'}, {'label':'B','conditional_percent':10,'minutes':2,'source_url':'https://example.com/b'}]
class FarmTests(unittest.TestCase):
 def test_conditional_probability_and_reached_stage_cost(self):
  r=farm.reward_chain(STAGES,20);self.assertAlmostEqual(r['conditional_success_probability'],.05);self.assertEqual(r['expected_active_minutes_per_attempt'],9);self.assertAlmostEqual(r['expected_minutes_to_first_success'],180);self.assertAlmostEqual(r['at_least_one_probability'],1-.95**20);self.assertEqual(r['stages'][1]['source_url'],'https://example.com/b')
 def test_retry_wait_after_failures_only(self):
  r=farm.reward_chain(STAGES,retry_wait_minutes=10);self.assertAlmostEqual(r['expected_minutes_to_first_success'],370)
 def test_impossible_route_and_no_attempts(self):
  r=farm.reward_chain([STAGES[0]|{'conditional_percent':0}],0);self.assertIsNone(r['expected_minutes_to_first_success']);self.assertEqual(r['at_least_one_probability'],0)
 def test_invalid_rate_cost_or_source(self):
  for change in [{'conditional_percent':math.nan},{'conditional_percent':101},{'minutes':-1},{'source_url':'https://user:password@example.com'}]:
   with self.assertRaises(ValueError):farm.reward_chain([STAGES[0]|change])
  with self.assertRaises(ValueError):farm.reward_chain([STAGES[0]|{'minutes':0}])
 def test_timezone_window_crosses_midnight(self):
  r=farm.revisit_window('2026-10-19T23:50:00-04:00',30,40);self.assertEqual(r['check_from'],'2026-10-20T00:20:00-04:00');self.assertEqual(r['check_until'],'2026-10-20T00:30:00-04:00')
 def test_window_needs_timezone_and_order(self):
  with self.assertRaises(ValueError):farm.revisit_window('2026-10-19T14:00:00',30,40)
  with self.assertRaises(ValueError):farm.revisit_window('2026-10-19T14:00:00Z',40,30)

if __name__=='__main__':unittest.main()
