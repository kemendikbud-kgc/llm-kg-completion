"""Extract specific section bodies from Main and Formatted Main for comparison."""
import json, re

d = json.load(open('thesis_full.json', encoding='utf-8'))
tabs = {t['tabProperties']['title']: t for t in d['tabs']}

def walk(tab):
    """Yield (style, text) per paragraph block (and table rows flattened)."""
    body = tab.get('documentTab', {}).get('body', {}).get('content', [])
    out = []
    for el in body:
        if 'paragraph' in el:
            p = el['paragraph']
            style = p.get('paragraphStyle', {}).get('namedStyleType', 'NORMAL_TEXT')
            text = ''.join((e.get('textRun', {}) or {}).get('content', '')
                           for e in p.get('elements', []))
            out.append((style, text))
        elif 'table' in el:
            t = el['table']
            for row in t.get('tableRows', []):
                cells = []
                for cell in row.get('tableCells', []):
                    s = ''
                    for sub in cell.get('content', []):
                        if 'paragraph' in sub:
                            s += ''.join((e.get('textRun', {}) or {}).get('content','')
                                         for e in sub['paragraph'].get('elements', []))
                    cells.append(s.strip())
                out.append(('TABLE_ROW', ' | '.join(cells)))
    return out

def section_body(blocks, heading_text, stop_at_level=None):
    """Return text from heading_text through next heading at same-or-higher level."""
    res = []
    started = False
    start_level = None
    for style, text in blocks:
        is_heading = style.startswith('HEADING_')
        level = int(style.split('_')[-1]) if is_heading else None
        if not started:
            if is_heading and heading_text.lower() in text.strip().lower():
                started = True
                start_level = level
                res.append(f'## {text.strip()}')
            continue
        # Stop when we hit another heading at <= start_level
        if is_heading and level <= start_level:
            break
        res.append(text.rstrip('\n'))
    return '\n'.join(res)

main = walk(tabs['Main'])
fmt  = walk(tabs['Formatted Main'])

print('=' * 80)
print('FORMATTED MAIN — "Parameter Sistem dan Definisi Operasional" section')
print('=' * 80)
print(section_body(fmt, 'Parameter Sistem dan Definisi Operasional'))

print('\n' + '=' * 80)
print('MAIN — "Kerangka Konsep" §3.6 (where param-like content used to live)')
print('=' * 80)
print(section_body(main, 'Kerangka Konsep'))

print('\n' + '=' * 80)
print('FORMATTED MAIN — "Description Completeness" (new metric)')
print('=' * 80)
print(section_body(fmt, 'Description Completeness'))

print('\n' + '=' * 80)
print('FORMATTED MAIN — "Empty SubKonsep Rate (ESR)" (new metric)')
print('=' * 80)
print(section_body(fmt, 'Empty SubKonsep Rate'))

print('\n' + '=' * 80)
print('FORMATTED MAIN — "Kekosongan Cakupan" (new pembahasan)')
print('=' * 80)
print(section_body(fmt, 'Kekosongan Cakupan'))
