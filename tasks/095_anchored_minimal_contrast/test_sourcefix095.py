import unittest
import method095 as m
import sourcefix095 as fix
class SourceFix(unittest.TestCase):
    def test_whitespace_only_and_original_offset(self):
        row=dict(text='The synthetic finding was mild.',reference='1. Date: D1 | Text: The synthetic finding was severe\n   and persistent.')
        v=dict(applicable=True,attribute='state',old_span='mild',new_span='severe and persistent',source_value='severe and persistent',anchors=[dict(reference_id=1,quote='The synthetic finding was severe and persistent.')])
        self.assertEqual(m.validate(v,row)['error'],'value_not_in_quote');f=fix.validate(v,row);self.assertTrue(f['valid']);a=f['anchors'][0];self.assertEqual(row['reference'][a['reference_start']:a['reference_end']],a['quote'])
        v['source_value']='serious';v['new_span']='serious';self.assertFalse(fix.validate(v,row)['valid'])
if __name__=='__main__':unittest.main()
