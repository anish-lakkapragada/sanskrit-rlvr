"""Offline transport invariants; no runner imports or provider calls."""
import copy
import random
import unittest

from misc.vp_cartesian_transport import partition_tasks


def partition(tasks, schedule, **overrides):
    args = dict(core_phase='hard_final', extension_phase='hard_extension', schedule=schedule)
    args.update(overrides)
    return partition_tasks(tasks, **args)


class TransportPartitionTests(unittest.TestCase):
    def test_fixed_4800_taper_preserves_order_metadata_and_core(self):
        tasks = [{'id': f'task-{i}', 'nested': {'accepted': [str(i), 'unchanged']}}
                 for i in range(4800)]
        before = copy.deepcopy(tasks)
        schedule = [(3000, 100), (4000, 50), (4600, 25), (4800, 5)]
        stages = partition(tasks, schedule)
        self.assertEqual(len(stages), 114)
        self.assertEqual([len(s['tasks']) for s in stages], [100] * 30 + [50] * 20 + [25] * 24 + [5] * 40)
        self.assertEqual([s['phase'] for s in stages], ['hard_final'] * 10 + ['hard_extension'] * 104)
        flattened = [t for s in stages for t in s['tasks']]
        self.assertEqual(flattened, before)
        self.assertTrue(all(a is b for a, b in zip(flattened, tasks)))
        self.assertEqual(tasks, before)
        self.assertEqual(schedule, [(3000, 100), (4000, 50), (4600, 25), (4800, 5)])

    def test_nondivisible_chunks_cut_at_core_and_segment_boundaries(self):
        stages = partition(list(range(1751)), [(1501, 333), (1751, 200)])
        self.assertEqual([len(s['tasks']) for s in stages], [333, 333, 333, 1, 333, 168, 200, 50])
        self.assertEqual(stages[3], {'phase': 'hard_final', 'tasks': [999]})
        self.assertEqual(stages[4]['tasks'][0], 1000)
        self.assertEqual(stages[-1]['tasks'][-1], 1750)

    def test_schedule_endpoint_before_core_does_not_start_extension_early(self):
        stages = partition(tuple(range(1200)), [(700, 600), (1200, 600)])
        self.assertEqual([len(s['tasks']) for s in stages], [600, 100, 300, 200])
        self.assertEqual([s['phase'] for s in stages], ['hard_final'] * 3 + ['hard_extension'])

    def test_small_fixed_n_and_exact_core_have_no_extension(self):
        for n in [1, 999, 1000]:
            with self.subTest(n=n):
                stages = partition(list(range(n)), [(n, 1000)])
                self.assertEqual(stages, [{'phase': 'hard_final', 'tasks': list(range(n))}])

    def test_first_extension_task_is_separate(self):
        stages = partition(list(range(1001)), [(1001, 1000)])
        self.assertEqual([len(s['tasks']) for s in stages], [1000, 1])
        self.assertEqual(stages[-1], {'phase': 'hard_extension', 'tasks': [1000]})

    def test_invalid_schedule_is_rejected_without_mutating_tasks(self):
        tasks = [{'id': str(i)} for i in range(1200)]
        before = copy.deepcopy(tasks)
        cases = [[], [(1199, 100)], [(1201, 100)], [(500, 100), (500, 10), (1200, 10)],
                 [(600, 10), (500, 10), (1200, 10)], [(0, 10), (1200, 10)],
                 [(True, 10), (1200, 10)], [(1200.0, 10)], [(1200, True)],
                 [(1200, 0)], [(1200, -1)], [(1200, 1001)], [(1200, 2.5)],
                 [(1200,)], [(1200, 20, 1)], ['12'], '1200,100']
        for schedule in cases:
            with self.subTest(schedule=schedule), self.assertRaises(ValueError):
                partition(tasks, schedule)
            self.assertEqual(tasks, before)

    def test_empty_or_unordered_input_and_invalid_phase_names_are_rejected(self):
        for tasks in [[], {}, {1, 2}, 'tasks', b'tasks']:
            with self.subTest(tasks=tasks), self.assertRaises(ValueError):
                partition(tasks, [(1, 1)])
        for changes in [{'core_phase': ''}, {'extension_phase': '  '},
                        {'core_phase': None}, {'extension_phase': 'hard_final'}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                partition([1], [(1, 1)], **changes)

    def test_json_style_schedule_and_generic_phase_names(self):
        self.assertEqual(partition([{'opaque': [1, 2]}], [[1, 1]],
                                   core_phase='core', extension_phase='extension'),
                         [{'phase': 'core', 'tasks': [{'opaque': [1, 2]}]}])

    def test_randomized_schedules_obey_partition_and_boundary_invariants(self):
        rng = random.Random(2026100709)
        for _ in range(100):
            n = rng.randint(1, 6000)
            endpoints = sorted(set([n] + [rng.randint(1, n) for _ in range(rng.randint(0, 12))]))
            schedule = [(end, rng.randint(1, 1000)) for end in endpoints]
            tasks = list(range(n))
            stages = partition(tasks, schedule)
            self.assertEqual([t for s in stages for t in s['tasks']], tasks)
            self.assertEqual(sum(len(s['tasks']) for s in stages if s['phase'] == 'hard_final'), min(n, 1000))
            boundaries = set()
            for stage in stages:
                values = stage['tasks']
                self.assertTrue(values)
                self.assertLessEqual(len(values), 1000)
                self.assertEqual(stage['phase'], 'hard_final' if values[-1] < 1000 else 'hard_extension')
                self.assertFalse(values[0] < 1000 <= values[-1])
                applicable_end, max_chunk = next((end, chunk) for end, chunk in schedule if values[0] < end)
                self.assertLessEqual(values[-1] + 1, applicable_end)
                self.assertLessEqual(len(values), max_chunk)
                boundaries.add(values[-1] + 1)
            self.assertTrue(set(endpoints).issubset(boundaries))
            self.assertIn(min(n, 1000), boundaries)


if __name__ == '__main__':
    unittest.main()
