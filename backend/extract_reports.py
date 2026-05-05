"""Extract structure and content from historical design reports."""
from docx import Document
import os

files = [
    (r'C:\Users\Administrator\Desktop\金牛研磨400td废水处理方案20240423.doc', 'jinniu'),
    (r'C:\Users\Administrator\Desktop\药物研究所废水方案20240905.docx', 'yaowu'),
    (r'C:\Users\Administrator\Desktop\星海化纤废水处理设计方案202210.doc', 'xinghai'),
]

for fpath, tag in files:
    if not os.path.exists(fpath):
        print(f'{tag}: FILE NOT FOUND at {fpath}')
        continue
    try:
        doc = Document(fpath)
        outlines = []
        para_count = 0
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            style = p.style.name if p.style else 'Normal'
            outlines.append(f'[{style}] {text}')
            para_count += 1

        output = os.path.join(r'E:\claude\wastewater-app', f'{tag}_structure.txt')
        with open(output, 'w', encoding='utf-8') as f:
            f.write(f'=== {tag} === ({para_count} non-empty paragraphs)\n\n')
            f.write('\n'.join(outlines))

        print(f'{tag}: OK, {para_count} paragraphs -> {output}')
    except Exception as e:
        print(f'{tag}: ERROR - {e}')
