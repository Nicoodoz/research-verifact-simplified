"""Display one full clinical reading page; omit only redundant transport metadata."""
import argparse,json,re
import common018 as c

def show(page):
    index=c.read(c.OUT/'review_001/page_index.json');entry=next(p for p in index if p['page']==page)
    path=c.OUT/'review_001'/entry['file'];c.require(c.file_hash(path)==entry['sha256'],'Reading page changed')
    text=path.read_text(encoding='utf-8')
    def outputs(match):
        data=json.loads(match.group(1));parts=['FULL CLINICAL OUTPUTS (transport metadata omitted)']
        for system,values in data.items():
            if system=='O':
                for field in ('reason','reasoning_chain','reasoning_final_answer'):parts.append(system+'/'+field+'\n'+(values[field] or ''))
            else:parts.append(system+'/output_text\n'+values['output_text'])
        return '\n\n'.join(parts)+'\nFULL REFERENCES'
    text=re.sub(r'FULL OUTPUTS\n(\{[^\n]+\})\nFULL REFERENCES',outputs,text)
    print(f"PAGE {page} CASE {entry['case_id']} PART {entry['part']}/{entry['parts']} SOURCE_SHA256 {entry['sha256']}\n{text}")

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('page',type=int);show(p.parse_args().page)
