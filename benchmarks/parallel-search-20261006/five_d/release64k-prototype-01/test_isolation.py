import unittest
class IsolationTests(unittest.TestCase):
    def test_guards_prevent_network_external_writes_and_live_ledger_reads(self):
        import socket,sitecustomize
        live=sitecustomize.ALLOWED.parents[3]
        with self.assertRaisesRegex(RuntimeError,'forbids network'):socket.socket()
        with self.assertRaisesRegex(RuntimeError,'write outside'): (live/'prototype-must-never-be-created.tmp').write_text('denied')
        with self.assertRaisesRegex(RuntimeError,'cannot read live'): (live/'benchmarks/iterative-goal-20261006/ledger.json').read_text()
        self.assertFalse((live/'prototype-must-never-be-created.tmp').exists())

