"""Label-blind exact outer-fence normalization; no JSON repair or text verdict search."""
import copy
import json
import re
import common099 as c

def parse(tr):
    strict=c.parse(tr)
    if strict['valid']:return dict(strict,outer_fence_removed=False,strict_valid=True)
    try:
        native=json.loads(tr['body_text']);content=native['choices'][0]['message']['content']
        assert isinstance(content,str)
        match=re.fullmatch(r'\s*```(?:json)?[ \t]*\r?\n(.*)\r?\n```\s*',content,re.DOTALL|re.IGNORECASE)
        assert match
        changed=copy.deepcopy(native);changed['choices'][0]['message']['content']=match[1]
        parsed=c.parse(dict(tr,body_text=json.dumps(changed)))
        return dict(parsed,outer_fence_removed=parsed['valid'],strict_valid=False)
    except (AssertionError,KeyError,TypeError,ValueError,IndexError):
        return dict(strict,outer_fence_removed=False,strict_valid=False)
