"""Preserve the pre-helper extraction version bound by the zero-API inventory."""
import common093 as c
def main():
    text=(c.TASK/'operation093.py').read_text(encoding='utf-8')
    a=text.index('def encode_with_dictionary');b=text.index('def parse',a)
    text=text[:a]+text[b:]
    old="""    reverse={v:k for k,v in dictionary.items()}
    body=prefix+''.join(v['header']+reverse.get(v['text'],v['text'])+v['separator'] for v in entries)
    packed=body+(TABLE+''.join(k+'\\n'+v+'\\n[[END_'+k[2:]+'\\n' for k,v in dictionary.items()) if dictionary else '')
"""
    text=text.replace("    packed,body=encode_with_dictionary(reference,dictionary)\n",old)
    path=c.OUT/'engineering_archive/operation_inventory_v1.py';path.parent.mkdir(parents=True,exist_ok=True)
    expected=c.read(c.OUT/'inventory_freeze.json')['operation_sha256']
    assert c.h(text)==expected,'must reproduce original bytes, never invent old source'
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    c.put(c.OUT/'engineering_archive/note.json',dict(original_sha256=expected,current_sha256=c.sha(c.TASK/'operation093.py'),change='Extract encode_with_dictionary helper for added-candidate rendering; factoring thresholds, grouping and original inventory outputs unchanged.',stage='before any paid request'))
    print('Original inventory source SHA verified and archived.')
if __name__=='__main__':main()
