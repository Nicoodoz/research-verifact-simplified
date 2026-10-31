"""Change only the unique global sort caption in the frozen142 reference."""
import re

OLD = 'Ordered by Time (Earliest to Latest):'
NEW = 'Ordered by BM25 Relevance (Highest to Lowest):'
HEADER = re.compile(r'(?m)^\d+\. Date: ')


def replace_caption(reference):
    first = HEADER.search(reference)
    if not first or reference.count(OLD) != 1:
        raise ValueError('Expected one exact global caption')
    start = reference.index(OLD)
    if start != 123 or start + len(OLD) > first.start():
        raise ValueError('Caption is not the previously audited global preamble')
    changed = reference[:start] + NEW + reference[start + len(OLD):]
    if reference[:start] + reference[start + len(OLD):] != changed[:start] + changed[start + len(NEW):]:
        raise AssertionError('A non-caption character changed')
    return changed, dict(start=start, old_end=start+len(OLD), new_end=start+len(NEW),
                         character_delta=len(NEW)-len(OLD), noncaption_characters_identical=True)
