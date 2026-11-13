"""Pure parser regressions with explicit synthetic log events; NOT native evidence."""
import unittest
from audited_log_records import audit_log_records

IDENT='0123456789abcdef0123456789abcdef'
HEADER='[12:00:00] [Download-1/ERROR]: Got an error with a html body connecting to https://sessionserver.mojang.com/session/minecraft/profile/'+IDENT+'?unsigned=false: <!DOCTYPE html>'
NEXT='[12:00:01] [Server thread/INFO]: Next event'

def log(text,file='server.actual.log',boot='enabled_initial'):return {'file':file,'boot':boot,'text':text}
def known(body='<html>status=429</html>'):return HEADER+'\n'+body+'\n'+NEXT

def audit(logs,**kwargs):
    return audit_log_records(logs,expected_ids={IDENT},actors_ok=True,owner_ok=True,closure_ok=True,**kwargs)

class NativeLogRecords(unittest.TestCase):
    def test_exact_optional_profile_429_event_requires_actual_prerequisites(self):
        r=audit([log(known())]);self.assertEqual(r['fatalErrors'],[]);self.assertEqual(len(r['allErrorLines']),1)
        self.assertEqual(len(r['nonfatalTransportWarnings']),1);self.assertEqual(r['records'][0]['rawEvent'],HEADER+'\n<html>status=429</html>')
        self.assertEqual(r['records'][0]['line1'],1);self.assertEqual(r['records'][0]['file'],'server.actual.log')
    def test_identical_header_uses_its_own_actual_line_body(self):
        text=known()+'\n'+known('<html>status=503</html>');r=audit([log(text)])
        self.assertEqual(r['allErrorLines'],[HEADER,HEADER]);self.assertEqual(len(r['nonfatalTransportWarnings']),1);self.assertEqual(r['fatalErrors'],[HEADER])
        self.assertEqual([x['line1']for x in r['records']],[1,4]);self.assertEqual(r['records'][1]['statusCodes'],['503'])
        self.assertIn('status=503',r['records'][1]['rawEvent']);self.assertNotIn('status=429',r['records'][1]['rawEvent'])
    def test_identical_header_different_boot_unknown_stack_remains_fatal(self):
        stack='<html>status=429</html>\njava.lang.IllegalStateException: unexpected\n\tat example.Native.work(Native.java:1)'
        r=audit([log(known()),log(known(stack),'server.default_off.log','default_off')])
        self.assertEqual(len(r['nonfatalTransportWarnings']),1);self.assertEqual(len(r['fatalErrors']),1)
        self.assertEqual(r['records'][1]['boot'],'default_off');self.assertEqual(r['records'][1]['line1'],1)
        self.assertIn('IllegalStateException',r['records'][1]['rawEvent'])
    def test_missing_or_false_identity_owner_or_closure_fails_closed(self):
        for missing in ['actors_ok','owner_ok','closure_ok']:
            for value in [None,False,1]:
                with self.subTest(field=missing,value=value):
                    flags={'actors_ok':True,'owner_ok':True,'closure_ok':True};flags[missing]=value
                    r=audit_log_records([log(known())],expected_ids={IDENT},**flags)
                    self.assertEqual(r['fatalErrors'],[HEADER]);self.assertEqual(r['nonfatalTransportWarnings'],[])
            flags={'actors_ok':True,'owner_ok':True,'closure_ok':True};flags.pop(missing)
            self.assertEqual(audit_log_records([log(known())],expected_ids={IDENT},**flags)['fatalErrors'],[HEADER])
    def test_unknown_missing_or_mixed_status_does_not_get_a_429_exception(self):
        for body in ['<html>Unknown error</html>','<html>status=500</html>','<html>status=429 status=500</html>']:
            with self.subTest(body=body):self.assertEqual(audit([log(known(body))])['fatalErrors'],[HEADER])
    def test_other_profile_uuid_and_other_error_are_strict(self):
        foreign=known().replace(IDENT,'f'*32);r=audit([log(foreign)])
        self.assertEqual(len(r['fatalErrors']),1)
        other='[12:00:00] [Server thread/ERROR]: Mixin apply failed status=429';r=audit([log(other)])
        self.assertEqual(r['fatalErrors'],[other]);self.assertEqual(r['records'][0]['rawEvent'],other)
    def test_file_boundary_cannot_supply_missing_status_to_prior_boot(self):
        r=audit([log(HEADER),log('<html>status=429</html>','server.enabled_reload.log','enabled_reload')])
        self.assertEqual(r['fatalErrors'],[HEADER]);self.assertEqual(r['records'][0]['rawEvent'],HEADER)
    def test_raw_error_and_multiline_event_are_retained_in_order(self):
        body='[12:00:00] [Server thread/ERROR]: native failure\njava.lang.RuntimeException: boom\n\tat example.Test.run(Test.java:1)\n'+NEXT
        r=audit([log(body)]);self.assertEqual(r['lineCount'],4);self.assertEqual(r['records'][0]['endLine1'],3)
        self.assertEqual(r['records'][0]['rawEvent'],body.rsplit('\n',1)[0]);self.assertTrue(r['records'][0]['fatal'])

if __name__=='__main__':unittest.main()
