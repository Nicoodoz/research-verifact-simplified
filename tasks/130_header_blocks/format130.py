"""Group adjacent identical metadata headers, preserving every text fragment."""
import re

HEADER = re.compile(r'(?m)^(\d+)\. (Date: [^\n]*? \| Text: )')
NOTICE = ('Selected evidence fragments are grouped only by adjacent identical metadata. '
          'Separate fragments are not asserted to be adjacent in the original note.\n')


def group_reference(source):
    matches = list(HEADER.finditer(source))
    if not matches:
        raise ValueError('No original reference fragment headers')
    prefix = source[:matches[0].start()]
    fragments = []
    for i, match in enumerate(matches):
        end = matches[i+1].start() if i+1 < len(matches) else len(source)
        fragments.append(dict(number=match.group(1), metadata=match.group(2),
            original_header=source[match.start():match.end()], text=source[match.end():end]))
    if len({r['number'] for r in fragments}) != len(fragments):
        raise ValueError('Original fragment numbers are not unique')
    if prefix+''.join(r['original_header']+r['text'] for r in fragments) != source:
        raise ValueError('Not a lossless source partition')
    rendered = [prefix, NOTICE]
    groups = 0
    previous = None
    for row in fragments:
        if row['metadata'] != previous:
            groups += 1
            rendered.append('\nHeader group '+str(groups)+': '+row['metadata'][:-len(' | Text: ')]+'\n')
            previous = row['metadata']
        rendered.append('[Fragment '+row['number']+']\n'+row['text'])
    return ''.join(rendered), fragments, dict(fragment_N=len(fragments),header_groups=groups,
        source_characters=len(source),rendered_characters=sum(map(len,rendered)),
        text_fields_byte_identical=True,fragment_order_unchanged=True,
        nonadjacent_headers_not_merged=True,no_claim_of_true_note_identity=True)
