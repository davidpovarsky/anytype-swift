"""Regression for excluding actual core UI PIDs from later R08 receipts."""
import ast
from pathlib import Path
import unittest


def load_function():
    source = Path(__file__).with_name('combined_host_acceptance_app15.py').read_text()
    tree = ast.parse(source)
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name == 'native_ui_prior_processes']
    def require(value, reason):
        if not value:
            raise ValueError(reason)
    namespace = {'require': require}
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<original-controller>', 'exec'), namespace)
    return namespace['native_ui_prior_processes']


class PriorProcessTests(unittest.TestCase):
    def test_actual_processes_are_excluded_instead_of_role_names(self):
        prior = load_function()({'preparationProcessID': 110},
            {'actual_processes': {'related-targets': [111, 111, 111],
                'note-lifecycle': [112, 112, 112, 112, 113, 113, 113]}})
        self.assertEqual(prior, {110, 111, 112, 113})
        for stale_pid in (110, 111, 112, 113):
            self.assertIn(stale_pid, prior)
        self.assertNotIn('note-lifecycle', prior)

    def test_changed_or_incomplete_original_inventory_is_rejected(self):
        invalid = [
            {'related-targets': [111], 'note-lifecycle': [112]},
            {'related-targets': [111], 'note-lifecycle': [110, 113]},
            {'related-targets': [111, 111], 'note-lifecycle': [111, 113, 113]},
            {'related-targets': [111, 112], 'note-lifecycle': [113, 114]},
            {'related-targets': [111], 'note-lifecycle': [112, 113, 114]},
            {'related-targets': [111], 'note-lifecycle': ['112', 113]},
            {'related-targets': [111], 'note-lifecycle': [True, 113]},
            {'related-targets': [111], 'unexpected': [112, 113]},
            {'related-targets': 111, 'note-lifecycle': [112, 113]},
        ]
        for processes in invalid:
            with self.subTest(processes=processes), self.assertRaises(ValueError):
                load_function()({'preparationProcessID': 110}, {'actual_processes': processes})


if __name__ == '__main__':
    unittest.main()
