from _fake import FakeClientCase


class ContentPageCountTests(FakeClientCase):
    def test_analysis_requires_content_capability_before_writing(self):
        self.responses = {('GET', '/capabilities'): {}}
        with self.assertRaisesRegex(ValueError, 'content|内容页'):
            self.cli('analysis', 'start', '3', '--page-count', '6')
        self.assertFalse(any(call[0] == 'POST' for call in self.calls))

    def test_disabled_capability_blocks_target_save(self):
        self.responses = {('GET', '/capabilities'): {'analysis_page_count': {'available': False, 'count_basis': 'content', 'min': 1, 'max': 50}}}
        with self.assertRaisesRegex(ValueError, 'content|内容页'):
            self.cli('source', 'set', '3', '--text', 'x', '--target-pages', '50')
        self.assertFalse(any(call[0] == 'PUT' for call in self.calls))

    def test_source_and_analysis_explicitly_confirm_content_basis(self):
        self.cli('source', 'set', '3', '--text', 'x', '--target-pages', '50')
        self.assertEqual(self.body()['count_basis'], 'content')
        self.assertEqual(self.body()['target_page_count'], 50)
        self.cli('analysis', 'start', '3', '--page-count', '6')
        self.assertEqual(self.body()['count_basis'], 'content')
        self.assertEqual(self.body()['page_count'], 6)

    def test_existing_operation_remains_readable_when_new_analysis_is_disabled(self):
        failure = {'schema_version': 'analysis_failure.v1', 'reason': 'content_capacity_exceeded',
                   'content_page_count': 6, 'next_action': 'review_source_settings'}
        self.responses = {('GET', '/capabilities'): {},
                          ('GET', '/operations/original'): {'run': {'status': 'failed', 'output_snapshot': {'analysis_failure': failure}}}}
        result = self.cli('operations', 'show', 'original')
        self.assertEqual(result['run']['output_snapshot']['analysis_failure'], failure)
        self.assertEqual([call[:2] for call in self.calls], [('GET', '/operations/original')])
