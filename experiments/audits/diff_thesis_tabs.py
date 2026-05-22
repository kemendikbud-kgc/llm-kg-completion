"""Diff the Main and Formatted Main tabs of the thesis doc."""
import json, os, re, difflib, sys

d = json.load(open('thesis_full.json', encoding='utf-8'))
tabs = {t['tabProperties']['title']: t for t in d['tabs']}

def extract_text_blocks(tab):
    """Yield (style, text) for each paragraph in the tab body."""
    out = []
    body = tab.get('documentTab', {}).get('body', {}).get('content', [])
    for el in body:
        if 'paragraph' in el:
            p = el['paragraph']
            style = p.get('paragraphStyle', {}).get('namedStyleType', 'NORMAL_TEXT')
            text = ''.join(
                (e.get('textRun', {}) or {}).get('content', '')
                for e in p.get('elements', [])
            )
            out.append((style, text))
        elif 'table' in el:
            t = el['table']
            for row in t.get('tableRows', []):
                row_text = []
                for cell in row.get('tableCells', []):
                    cell_text = ''
                    for sub in cell.get('content', []):
                        if 'paragraph' in sub:
                            cell_text += ''.join(
                                (e.get('textRun', {}) or {}).get('content', '')
                                for e in sub['paragraph'].get('elements', [])
                            )
                    row_text.append(cell_text.strip())
                out.append(('TABLE_ROW', ' | '.join(row_text) + '\n'))
        elif 'sectionBreak' in el:
            out.append(('SECTION', '\n---\n'))
    return out

main_blocks = extract_text_blocks(tabs['Main'])
fmt_blocks  = extract_text_blocks(tabs['Formatted Main'])

print(f'Main           : {len(main_blocks)} blocks, '
      f'{sum(len(t) for _,t in main_blocks)} chars')
print(f'Formatted Main : {len(fmt_blocks)} blocks, '
      f'{sum(len(t) for _,t in fmt_blocks)} chars')

# Headings outline of each (HEADING_1..6)
def outline(blocks):
    h = []
    for style, text in blocks:
        if style.startswith('HEADING_') or style == 'TITLE':
            txt = text.strip()
            if txt:
                lvl = 0 if style == 'TITLE' else int(style.split('_')[-1])
                h.append((lvl, txt))
    return h

main_outline = outline(main_blocks)
fmt_outline  = outline(fmt_blocks)

print(f'\n--- Main outline ({len(main_outline)} headings) ---')
for lvl, t in main_outline:
    print(f'  {"  "*lvl}{"#"*max(lvl,1)} {t}')
print(f'\n--- Formatted Main outline ({len(fmt_outline)} headings) ---')
for lvl, t in fmt_outline:
    print(f'  {"  "*lvl}{"#"*max(lvl,1)} {t}')

# Save flattened text for diff
def flatten(blocks):
    return ''.join(t for _, t in blocks)

main_text = flatten(main_blocks)
fmt_text  = flatten(fmt_blocks)
open('main_text.txt', 'w', encoding='utf-8').write(main_text)
open('fmt_text.txt', 'w', encoding='utf-8').write(fmt_text)
print(f'\nWrote main_text.txt ({len(main_text)} chars) and fmt_text.txt ({len(fmt_text)} chars)')

# Heading set comparison
main_h_set = {t for _,t in main_outline}
fmt_h_set  = {t for _,t in fmt_outline}
only_main = main_h_set - fmt_h_set
only_fmt  = fmt_h_set - main_h_set
print(f'\nHeadings only in Main           ({len(only_main)}):')
for t in sorted(only_main): print(f'  - {t}')
print(f'\nHeadings only in Formatted Main ({len(only_fmt)}):')
for t in sorted(only_fmt): print(f'  - {t}')
