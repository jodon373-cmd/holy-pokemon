"""Optional mocked CLI integration: import -> persistent queue -> output without network."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from holy_pokemon.automated_discovery import main


class CLIIntegration(unittest.TestCase):
    def test_offline_csv_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'input.csv'
            with path.open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=('title', 'source_url', 'ask'))
                writer.writeheader()
                writer.writerow({
                    'title': 'SYNTHETIC 2002 Expedition Pokemon PSA 9 card',
                    'source_url': 'https://www.ebay.com/itm/123456', 'ask': '250'})
            rc = main(['--import-csv', str(path), '--database', str(Path(d)/'state.sqlite'),
                       '--output', str(Path(d)/'out'), '--once'])
            self.assertEqual(rc, 0)
            report = json.loads((Path(d)/'out/research_leads.json').read_text())
            self.assertEqual(report['count'], 1)
            self.assertIsNone(report['leads'][0]['economic_profit'])
            self.assertTrue((Path(d)/'out/research_leads.csv').exists())


if __name__ == '__main__':
    unittest.main()