from pathlib import Path
import re

from django.conf import settings
from django.test import SimpleTestCase


class AdminCoordinationHoursSpacingTests(SimpleTestCase):
    def setUp(self):
        self.css = (Path(settings.BASE_DIR) / 'static/css/r1_admin_coordination_logs.css').read_text()

    def test_only_status_hours_widths_rebalanced_with_notes_boundary_preserved(self):
        widths = re.findall(r'\.r1-coordination-table col:nth-child\(\d\) \{ width:(\d+)%; \}', self.css)
        self.assertEqual(widths, ['5', '12', '14', '14', '13', '8', '8', '18', '8'])
        self.assertEqual(sum(map(int, widths)), 100)

    def test_hours_header_and_values_centered_without_changing_actions(self):
        desktop = self.css.split('@media (max-width:760px)', 1)[0]
        self.assertIn('.r1-admin-coordination-logs .r1-coordination-table .numeric-cell { text-align:center; }', desktop)
        self.assertIn('.r1-admin-coordination-logs .r1-coordination-table .actions-heading { text-align:right; }', desktop)
        self.assertIn('td.service-log-actions-cell { display:table-cell; text-align:right;', desktop)

    def test_mobile_record_rows_retain_existing_left_alignment(self):
        mobile = self.css.split('@media (max-width:760px)', 1)[1]
        self.assertIn('.r1-coordination-table :is(.numeric-cell,.actions-heading) { text-align:left; }', mobile)
        self.assertIn('.r1-coordination-table colgroup { display:none; }', mobile)
        self.assertIn('.r1-coordination-table td { width:auto; display:grid;', mobile)
