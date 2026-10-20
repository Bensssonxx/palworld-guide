"""Check numerical boundaries and source routing; no external accounts or game files."""
import importlib.util
import math
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'palworld-guide/scripts/guide_tools.py'
spec = importlib.util.spec_from_file_location('guide_tools', path)
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


class LootTests(unittest.TestCase):
    def test_known_probability(self):
        result = tools.loot_odds(3, 100)
        self.assertAlmostEqual(result['at_least_one_probability'], 1 - 0.97**100)
        self.assertEqual(result['runs_for_target_probability'], 99)
        self.assertAlmostEqual(result['expected_first_success_runs'], 100/3)

    def test_boundary_probabilities(self):
        self.assertEqual(tools.loot_odds(100, 0)['at_least_one_probability'], 0)
        self.assertEqual(tools.loot_odds(100, 1)['at_least_one_probability'], 1)
        zero = tools.loot_odds(0, 100)
        self.assertIsNone(zero['runs_for_target_probability'])
        self.assertIsNone(zero['expected_first_success_runs'])
        self.assertEqual(zero['at_least_one_probability'], 0)

    def test_target_is_minimum_sufficient_runs(self):
        for p in (0.000001, 0.3, 3, 50, 99.99):
            result = tools.loot_odds(p, 1, 0.95)
            n = result['runs_for_target_probability']
            self.assertGreaterEqual(tools.loot_odds(p,n)['at_least_one_probability'], 0.95)
            self.assertLess(tools.loot_odds(p,n-1)['at_least_one_probability'], 0.95)

    def test_invalid_rates_and_attempts(self):
        for p in (-1, 101, math.inf, math.nan):
            with self.assertRaises(ValueError): tools.loot_odds(p, 1)
        for n in (-1, 2.5, True, 10**13):
            with self.assertRaises(ValueError): tools.loot_odds(3,n)
        for q in (0, 1, math.nan):
            with self.assertRaises(ValueError): tools.loot_odds(3,1,q)

    def test_small_probability_stays_nonzero(self):
        self.assertGreater(tools.loot_odds(1e-12, 100)['at_least_one_probability'],0)


class PlanningTests(unittest.TestCase):
    def test_all_topics_route_to_relevant_sources(self):
        for topic in tools.load_reference('topics.json'):
            plan = tools.make_plan(topic, '示例需求')
            self.assertTrue(plan['source_entries'])
            self.assertTrue(all(topic in s['topics'] for s in plan['source_entries']))
            self.assertIsNone(plan['context']['version'])
            self.assertIsNone(plan['context']['level'])
            self.assertEqual(plan['status'],'research-plan-not-verified-answer')

    def test_explicit_context_and_host_are_preserved(self):
        plan = tools.make_plan('mount','只比较陆地坐骑',52,'1.0.5','coop','Steam','claude')
        self.assertEqual(plan['context']['level'],52)
        self.assertTrue(plan['prompt'].startswith('/palworld-guide'))
        self.assertIn('只比较陆地坐骑', plan['prompt'])

    def test_invalid_context(self):
        for changes in ({'level':0},{'mode':'made-up'},{'goal':' '},{'topic':'other'}):
            args = {'topic':'map','goal':'找矿点'} | changes
            with self.assertRaises(ValueError): tools.make_plan(**args)


if __name__ == '__main__':
    unittest.main()
