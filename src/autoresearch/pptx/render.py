"""Render a DeckPlan to a .pptx file."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu, Inches, Pt

from ..state import ContentBlock, DeckPlan, SlidePlan

Renderer = Callable[[object, ContentBlock], None]


def _render_title(slide, block: ContentBlock) -> None:
    if slide.shapes.title is not None:
        slide.shapes.title.text = block.title or ""


def _render_bullets(slide, block: ContentBlock) -> None:
    box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(5))
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(block.body.get("items", [])):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = str(item)
        p.font.size = Pt(18)


def _render_quiz(slide, block: ContentBlock) -> None:
    items = [block.body.get("question", "")]
    items += [f"{chr(65 + i)}. {opt}" for i, opt in enumerate(block.body.get("options", []))]
    answer = block.body.get("answer")
    if answer is not None:
        items.append(f"Answer: {answer}")
    _render_bullets(slide, ContentBlock(kind="bullets", body={"items": items}))


def _render_scenario(slide, block: ContentBlock) -> None:
    items = [
        f"Scenario: {block.body.get('scenario', '')}",
        f"Question: {block.body.get('question', '')}",
    ]
    for i, choice in enumerate(block.body.get("choices", []) or []):
        items.append(f"{chr(65 + i)}. {choice}")
    if block.body.get("debrief"):
        items.append(f"Debrief: {block.body['debrief']}")
    _render_bullets(slide, ContentBlock(kind="bullets", body={"items": items}))


def _render_infographic(slide, block: ContentBlock) -> None:
    """Title + 3–5 stat tiles + caption.

    body schema: {"tiles": [{"value": str, "label": str}, ...], "caption": str}
    """
    if block.title:
        tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(9), Inches(0.7))
        tb.text_frame.text = block.title
        tb.text_frame.paragraphs[0].font.size = Pt(24)
        tb.text_frame.paragraphs[0].font.bold = True

    tiles = block.body.get("tiles", [])[:5]
    if tiles:
        n = len(tiles)
        gap = Inches(0.25)
        total_w = Inches(9)
        tile_w = Emu(int((total_w - gap * (n - 1)) / n))
        tile_h = Inches(2.0)
        top = Inches(1.5)
        left0 = Inches(0.5)
        for i, tile in enumerate(tiles):
            left = Emu(int(left0 + i * (tile_w + gap)))
            shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, tile_w, tile_h)
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(0xE8, 0xF0, 0xFE)
            shape.line.color.rgb = RGBColor(0x1A, 0x73, 0xE8)
            tf = shape.text_frame
            tf.word_wrap = True
            tf.text = str(tile.get("value", ""))
            tf.paragraphs[0].font.size = Pt(28)
            tf.paragraphs[0].font.bold = True
            p = tf.add_paragraph()
            p.text = str(tile.get("label", ""))
            p.font.size = Pt(12)

    caption = block.body.get("caption")
    if caption:
        cb = slide.shapes.add_textbox(Inches(0.5), Inches(4.0), Inches(9), Inches(1.0))
        cb.text_frame.text = caption
        cb.text_frame.paragraphs[0].font.size = Pt(14)


def _render_flowchart(slide, block: ContentBlock) -> None:
    """Linear flowchart of labelled nodes connected by arrows.

    body schema: {"steps": [str, ...]}
    """
    steps = block.body.get("steps", [])
    if not steps:
        return
    if block.title:
        tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(9), Inches(0.7))
        tb.text_frame.text = block.title
        tb.text_frame.paragraphs[0].font.size = Pt(22)
        tb.text_frame.paragraphs[0].font.bold = True

    n = len(steps)
    gap = Inches(0.2)
    total_w = Inches(9)
    box_w = Emu(int((total_w - gap * (n - 1)) / n))
    box_h = Inches(1.2)
    top = Inches(2.5)
    left0 = Inches(0.5)
    centers = []
    for i, label in enumerate(steps):
        left = Emu(int(left0 + i * (box_w + gap)))
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, box_w, box_h)
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(0xFF, 0xF4, 0xE5)
        shape.line.color.rgb = RGBColor(0xF5, 0x9E, 0x0B)
        tf = shape.text_frame
        tf.word_wrap = True
        tf.text = str(label)
        tf.paragraphs[0].font.size = Pt(14)
        centers.append((left + box_w, top + box_h // 2))
    # Connectors
    for i in range(n - 1):
        x1, y = centers[i]
        x2 = x1 + gap
        connector = slide.shapes.add_connector(1, x1, y, x2, y)  # 1 = STRAIGHT
        connector.line.color.rgb = RGBColor(0x6B, 0x72, 0x80)


def _render_diagram(slide, block: ContentBlock) -> None:
    """Simple labelled concept map: a central node with N satellites.

    body schema: {"center": str, "nodes": [str, ...]}
    """
    center_label = block.body.get("center", "")
    nodes = block.body.get("nodes", [])
    cx, cy = Inches(5), Inches(3.75)
    cw, ch = Inches(2), Inches(1)
    central = slide.shapes.add_shape(MSO_SHAPE.OVAL, cx - cw // 2, cy - ch // 2, cw, ch)
    central.fill.solid()
    central.fill.fore_color.rgb = RGBColor(0x1A, 0x73, 0xE8)
    tf = central.text_frame
    tf.text = str(center_label)
    tf.paragraphs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    tf.paragraphs[0].font.size = Pt(14)

    if not nodes:
        return
    import math

    radius = Inches(2.5)
    for i, label in enumerate(nodes):
        angle = 2 * math.pi * i / len(nodes)
        nx = int(cx + radius * math.cos(angle))
        ny = int(cy + radius * math.sin(angle))
        nw, nh = Inches(1.8), Inches(0.7)
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, nx - nw // 2, ny - nh // 2, nw, nh
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(0xE8, 0xF0, 0xFE)
        shape.text_frame.text = str(label)
        shape.text_frame.paragraphs[0].font.size = Pt(11)
        slide.shapes.add_connector(1, cx, cy, nx, ny).line.color.rgb = RGBColor(0x9C, 0xA3, 0xAF)


def _render_table(slide, block: ContentBlock) -> None:
    """Render a table.

    body schema: {"headers": [str, ...], "rows": [[str, ...], ...]}
    """
    headers = block.body.get("headers", [])
    rows = block.body.get("rows", [])
    if not headers or not rows:
        return
    if block.title:
        tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(9), Inches(0.7))
        tb.text_frame.text = block.title
        tb.text_frame.paragraphs[0].font.size = Pt(22)
        tb.text_frame.paragraphs[0].font.bold = True

    n_cols = len(headers)
    n_rows = len(rows) + 1
    table_shape = slide.shapes.add_table(
        n_rows, n_cols, Inches(0.5), Inches(1.5), Inches(9), Inches(0.5 * n_rows + 0.5)
    )
    table = table_shape.table
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = str(h)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(0x1A, 0x73, 0xE8)
        for p in cell.text_frame.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                r.font.bold = True
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row[:n_cols]):
            table.cell(i, j).text = str(val)


def _render_image(slide, block: ContentBlock) -> None:
    """Render an image with caption.

    body schema: {"path": str | None, "prompt": str | None, "caption": str | None}
    Falls back to a placeholder rectangle if no path is provided.
    """
    path = block.body.get("path")
    if block.title:
        tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(9), Inches(0.7))
        tb.text_frame.text = block.title
        tb.text_frame.paragraphs[0].font.size = Pt(22)
        tb.text_frame.paragraphs[0].font.bold = True

    if path and Path(path).exists():
        slide.shapes.add_picture(path, Inches(2), Inches(1.5), height=Inches(4.5))
    else:
        # Placeholder so the slide still renders during dev/tests.
        ph = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(2), Inches(1.5), Inches(6), Inches(4)
        )
        ph.fill.solid()
        ph.fill.fore_color.rgb = RGBColor(0xF3, 0xF4, 0xF6)
        ph.line.color.rgb = RGBColor(0x9C, 0xA3, 0xAF)
        ph.text_frame.text = f"[image] {block.body.get('prompt', 'no prompt')}"
        ph.text_frame.paragraphs[0].font.size = Pt(14)
        ph.text_frame.paragraphs[0].font.italic = True

    caption = block.body.get("caption")
    if caption:
        cb = slide.shapes.add_textbox(Inches(0.5), Inches(6.1), Inches(9), Inches(0.6))
        cb.text_frame.text = caption
        cb.text_frame.paragraphs[0].font.size = Pt(12)
        cb.text_frame.paragraphs[0].font.italic = True


RENDERERS: dict[str, Renderer] = {
    "title": _render_title,
    "bullets": _render_bullets,
    "quiz": _render_quiz,
    "scenario": _render_scenario,
    "infographic": _render_infographic,
    "flowchart": _render_flowchart,
    "diagram": _render_diagram,
    "table": _render_table,
    "image": _render_image,
}


def render_deck(plan: DeckPlan, out: Path | str) -> Path:
    prs = Presentation()
    for slide_plan in plan.slides:
        _render_slide(prs, slide_plan)
    out_path = Path(out)
    prs.save(out_path)
    return out_path


def _render_slide(prs: Presentation, slide_plan: SlidePlan) -> None:
    layout = prs.slide_layouts[5]  # Title Only — content drawn manually
    slide = prs.slides.add_slide(layout)
    for block in slide_plan.blocks:
        renderer = RENDERERS.get(block.kind)
        if renderer is None:
            # Fallback: best-effort bullet dump so unknown kinds still render.
            _render_bullets(slide, ContentBlock(kind="bullets", body={"items": [block.kind]}))
        else:
            renderer(slide, block)
    if slide_plan.speaker_notes:
        slide.notes_slide.notes_text_frame.text = slide_plan.speaker_notes
