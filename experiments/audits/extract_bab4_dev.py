"""Extract the full body of 'Bab 4 Dev' tab from the cached thesis doc."""
import json, os
d = json.load(open('thesis_full.json', encoding='utf-8'))
tabs = {t['tabProperties']['title']: t for t in d['tabs']}

tab = tabs['Bab 4 Dev']
body = tab.get('documentTab', {}).get('body', {}).get('content', [])

# Render structurally
def walk(body, indent=0):
    out = []
    for el in body:
        if 'paragraph' in el:
            p = el['paragraph']
            style = p.get('paragraphStyle', {}).get('namedStyleType', 'NORMAL_TEXT')
            text = ''.join((e.get('textRun', {}) or {}).get('content','')
                           for e in p.get('elements', []))
            text = text.rstrip('\n')
            if not text.strip():
                continue
            if style.startswith('HEADING_'):
                lvl = int(style.split('_')[-1])
                out.append(f'{"#"*lvl} {text}')
            elif style == 'TITLE':
                out.append(f'# {text}  [TITLE]')
            else:
                out.append(text)
        elif 'table' in el:
            t = el['table']
            for ri, row in enumerate(t.get('tableRows', [])):
                cells = []
                for cell in row.get('tableCells', []):
                    s = ''
                    for sub in cell.get('content', []):
                        if 'paragraph' in sub:
                            s += ''.join((e.get('textRun', {}) or {}).get('content','')
                                         for e in sub['paragraph'].get('elements', []))
                    cells.append(s.strip())
                out.append('| ' + ' | '.join(cells) + ' |')
            out.append('')
    return out

lines = walk(body)
print(f'Bab 4 Dev: {len(body)} body items, {len(lines)} non-empty lines\n')
print('\n'.join(lines))
