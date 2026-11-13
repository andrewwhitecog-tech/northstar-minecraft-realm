"""Prepared unittest cases against actual retained error records. Not native acceptance."""
import json
from pathlib import Path
import unittest
from offline_service_records import assess,audit_error_lines


class ExactOfflineRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=json.loads(Path(__file__).with_name('ACTUAL_ERROR_RECORDS.json').read_text(encoding='utf8'))['records']
        cls.text='\n'.join('[06:56:31] [%s/%s]: %s\n%s'%(r['thread'],r['level'],r['message'],'\n'.join(r['body']))for r in cls.rows)
    def test_default_blocks_the_actual_two_service_records(self):
        result=assess(self.text)
        self.assertEqual(len(result['blockingErrorRecords']),len(self.rows))
        self.assertFalse(result['offlineServiceDiagnostics'])
        self.assertFalse(assess(self.text,offline_fixture=1)['offlineServiceDiagnostics'])
    def test_explicit_offline_matches_only_complete_actual_stacks(self):
        result=assess(self.text,offline_fixture=True)
        self.assertEqual([r['message']for r in result['offlineServiceDiagnostics']],[r['message']for r in self.rows])
        self.assertEqual(result['blockingErrorRecords'],[])
        self.assertFalse(result['rendererAccepted']);self.assertFalse(result['humanVisualAccepted'])
    def test_fatal_unknown_render_error_and_malformed_header_stay_blocking(self):
        for extra in ('[06:57:00] [Render thread/ERROR]: Failed to create framebuffer',
                      '[06:57:00] [Download-2/FATAL]: Failed to fetch user properties',
                      '[malformed] [Download-2/ERROR]: Failed to fetch user properties'):
            with self.subTest(extra=extra):
                result=assess(self.text+'\n'+extra,offline_fixture=True)
                self.assertEqual(len(result['blockingErrorRecords']),1)
                self.assertEqual(len(result['offlineServiceDiagnostics']),len(self.rows))
    def test_extra_exception_wrong_thread_or_status_cannot_hide(self):
        for text in (self.text.replace('Status: 401','Status: 500'),
                     self.text.replace('Download-2/ERROR','Render thread/ERROR'),
                     self.text.replace('com.mojang.authlib.exceptions.InvalidCredentialsException: Status: 401',
                                       'com.mojang.authlib.exceptions.InvalidCredentialsException: Status: 401\nCaused by: renderer failure')):
            with self.subTest(text=text):
                result=assess(text,offline_fixture=True)
                self.assertEqual(len(result['blockingErrorRecords']),1)
                self.assertEqual(len(result['offlineServiceDiagnostics']),1)

    def test_capture_audit_keeps_unknown_record_with_identical_header(self):
        row=self.rows[0];header='[06:56:31] [%s/%s]: %s'%(row['thread'],row['level'],row['message'])
        exact=header+'\n'+'\n'.join(row['body'])
        unknown=header+'\n'+'\n'.join(row['body'])+'\nCaused by: unexpected framebuffer failure'
        result=audit_error_lines(exact+'\n'+unknown,offline_fixture=True)
        self.assertEqual(len(result['offlineServiceDiagnostics']),1)
        self.assertEqual(len(result['blockingErrorRecords']),1)
        self.assertEqual(result['rawErrorHeaders'],[header,header])
        self.assertEqual(result['blockingLines'],[header])
    def test_capture_audit_preserves_nonerror_resource_failures_and_default_strict(self):
        resource='[06:57:00] [Render thread/WARN]: Failed to load texture nsp_cat_coats:bad'
        result=audit_error_lines(self.text+'\n'+resource,offline_fixture=True)
        self.assertEqual(result['blockingLines'],[resource])
        self.assertEqual(len(audit_error_lines(self.text)['blockingLines']),len(self.rows))


if __name__=='__main__':unittest.main()
