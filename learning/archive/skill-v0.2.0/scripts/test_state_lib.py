"""Regression tests use temporary files only; never touch learning records."""
import tempfile
import unittest
from pathlib import Path

from state_lib import CONCEPT_COLUMNS, read_mistakes, read_table, replace_table


class StateParsingTests(unittest.TestCase):
    def test_empty_field_does_not_consume_next_field(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'mistakes.md'
            path.write_text('## blank-review\n- **last_review**:\n- **next_review**: 2026-09-30\n', encoding='utf-8')
            record = read_mistakes(path)[0]
            self.assertEqual(record['last_review'], '')
            self.assertEqual(record['next_review'], '2026-09-30')

    def test_pipe_survives_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'concepts.md'
            path.write_text('| ' + ' | '.join(CONCEPT_COLUMNS) + ' |\n|' + '|'.join(['---'] * len(CONCEPT_COLUMNS)) + '|\n', encoding='utf-8')
            record = dict.fromkeys(CONCEPT_COLUMNS, '')
            record.update(id='union-type', notes='Task | None')
            replace_table(path, CONCEPT_COLUMNS, [record])
            self.assertEqual(read_table(path, CONCEPT_COLUMNS)[0], [record])

    def test_bad_row_fails_without_rewriting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'concepts.md'
            content = '| ' + ' | '.join(CONCEPT_COLUMNS) + ' |\n|' + '|'.join(['---'] * len(CONCEPT_COLUMNS)) + '|\n| broken | row |\n'
            path.write_text(content, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Malformed table row'):
                replace_table(path, CONCEPT_COLUMNS, [])
            self.assertEqual(path.read_text(encoding='utf-8'), content)


if __name__ == '__main__':
    unittest.main()
