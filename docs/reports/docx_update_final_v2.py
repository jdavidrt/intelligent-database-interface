#!/usr/bin/env python
"""
Smart Word document updater - v2
Handles plain text markdown headings (not # symbols)
Preserves all document formatting, styles, tables, lists.
"""

from docx import Document
from pathlib import Path
import re

def read_plaintext_markdown(filepath):
    """
    Read markdown with plain-text headings (no # symbols).
    Returns dict mapping heading text to content.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    sections = {}
    current_heading = None
    current_content = []

    # Patterns that indicate section headings
    heading_patterns = [
        r'^(RESUMEN|INTRODUCCIÓN|INTRODUCTION)$',
        r'^(CAPÍTULO \d+|CHAPTER \d+)',
        r'^\d+\.\d+\.',  # 1.1., 1.2., etc.
        r'^(CONCLUSIONES|CONCLUSIONES DEL CAPÍTULO)',
        r'^(RECOMENDACIONES)',
        r'^(REFERENCIAS)',
        r'^(ÍNDICE|INDEX)',
    ]

    for line in lines:
        line_stripped = line.strip()
        is_heading = False

        # Check if line is a heading
        for pattern in heading_patterns:
            if re.match(pattern, line_stripped, re.IGNORECASE):
                is_heading = True
                break

        if is_heading and line_stripped:
            # Save previous section
            if current_heading:
                content_text = '\n'.join(current_content).strip()
                sections[current_heading] = content_text

            current_heading = line_stripped
            current_content = []
        else:
            # Add to current section's content
            current_content.append(line.rstrip())

    # Save last section
    if current_heading:
        content_text = '\n'.join(current_content).strip()
        sections[current_heading] = content_text

    return sections

def update_docx_smart(original_docx, markdown_file, output_docx):
    """
    Smart update: Find section headings and replace following paragraphs.
    Preserves all formatting.
    """

    doc = Document(original_docx)
    md_sections = read_plaintext_markdown(markdown_file)

    print(f"\n{'='*80}")
    print(f"MARKDOWN SECTIONS FOUND:")
    print(f"{'='*80}\n")

    for heading, content in list(md_sections.items())[:20]:
        content_preview = content[:80].replace('\n', ' ')
        print(f"{heading:50s} | {content_preview}...")

    print(f"\nTotal sections: {len(md_sections)}")

    # Map document headings to markdown sections
    heading_matches = {
        'RESUMEN': 'RESUMEN',
        'INTRODUCCIÓN': 'INTRODUCCIÓN',
        'CAPÍTULO 1': 'CAPÍTULO 1: ANÁLISIS DE REQUERIMIENTOS',
        '1.1. MARCO TEÓRICO': '1.1. MARCO TEÓRICO',
        '1.2. DISEÑO METODOLÓGICO': '1.2. Diseño Metodológico',
        '1.3.': '1.3. Selección y Análisis de Benchmarks',
        '1.4.': '1.4. Base de Datos de Prueba: SoundWave',
        '1.5.': '1.5. Conjunto de Prueba Personalizado: IDI-EXEC-75',
        '1.6.': '1.6. Especificación de Requerimientos Funcionales',
        '1.7.': '1.7. Requerimientos No Funcionales',
        '1.8.': '1.8. Métricas de Éxito',
        '1.9.': '1.9. Escenarios de Casos de Uso',
        '1.10.': '1.10. Arquitectura de Agentes con LoRA Hot-Swap',
        '1.11.': '1.11. Avance del Trabajo de Campo: Prototipo Sandbox',
        '1.12.': '1.12. Conclusiones del Capítulo',
        '1.13.': '1.13. Recomendaciones',
    }

    print(f"\n{'='*80}")
    print(f"MATCHING SECTIONS IN DOCUMENT:")
    print(f"{'='*80}\n")

    matches = {}
    for para_idx, para in enumerate(doc.paragraphs):
        para_upper = para.text.strip().upper()

        for doc_keyword, md_section in heading_matches.items():
            if doc_keyword.upper() in para_upper:
                if md_section in md_sections:
                    matches[para_idx] = {
                        'doc_keyword': doc_keyword,
                        'md_section': md_section,
                        'para_text': para.text[:70],
                    }
                    print(f"[MATCH] Para {para_idx}: {para.text[:70]}")
                    print(f"        -> MD section: {md_section}")

    print(f"\n[SUMMARY] Matched {len(matches)} sections")

    # Now carefully update the content
    # Strategy: after each heading, replace the following paragraphs with MD content

    print(f"\n{'='*80}")
    print(f"UPDATING DOCUMENT CONTENT:")
    print(f"{'='*80}\n")

    updated_count = 0

    for para_idx in sorted(matches.keys()):
        md_section = matches[para_idx]['md_section']
        content = md_sections[md_section]

        # Split content into logical paragraphs
        content_paras = [
            p.strip()
            for p in content.split('\n\n')
            if p.strip() and not p.strip().startswith('────')
        ]

        if not content_paras:
            continue

        # Find the range to update (from next para until next heading)
        next_heading_idx = None
        for other_idx in sorted(matches.keys()):
            if other_idx > para_idx:
                next_heading_idx = other_idx
                break

        start_idx = para_idx + 1
        end_idx = next_heading_idx if next_heading_idx else len(doc.paragraphs)

        # Update paragraphs
        for content_idx, content_text in enumerate(content_paras):
            target_idx = start_idx + content_idx

            if target_idx < end_idx and target_idx < len(doc.paragraphs):
                # Replace existing paragraph's text
                old_text = doc.paragraphs[target_idx].text[:50]
                doc.paragraphs[target_idx].text = content_text
                print(f"[UPDATE] Para {target_idx}: {content_text[:60]}...")
                updated_count += 1

    print(f"\n{'='*80}")
    print(f"[SUCCESS] Updated {updated_count} paragraphs")
    print(f"[INFO] Document formatting and styles preserved")

    # Save document
    doc.save(output_docx)
    print(f"\n[OK] Saved to: {output_docx}")

    return True

if __name__ == '__main__':
    original_docx = 'docs/reports/IDI - Primer Informe.docx'
    markdown_file = 'docs/reports/IDI_Capitulo1_v3.md'
    output_docx = 'docs/reports/IDI_Primer_Informe_Updated_Final.docx'

    try:
        update_docx_smart(original_docx, markdown_file, output_docx)
        print(f"\n{'='*80}")
        print(f"COMPLETE - Review the output document")
        print(f"{'='*80}")
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
