from pathlib import Path

import fitz

from enterprise_rag.config import settings
from enterprise_rag.io import write_jsonl
from enterprise_rag.models import ChunkRecord, PageRecord, SearchHit
from enterprise_rag.visuals import render_page_image, visual_for_hit


def test_visual_snapshot_url_and_render(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "processed"
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()
    monkeypatch.setattr(settings, "data_dir", data_dir)

    pdf_path = uploads_dir / "visual.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "A page with a diagram or table can be rendered.")
    document.save(pdf_path)
    document.close()

    write_jsonl(
        data_dir / "pages.jsonl",
        [
            PageRecord(
                document_id="doc1",
                source_file="visual.pdf",
                page_number=1,
                text="A page with a diagram or table can be rendered.",
                extraction_method="native",
                quality_score=1.0,
            )
        ],
    )
    hit = SearchHit(
        score=1.0,
        chunk=ChunkRecord(
            chunk_id="chunk1",
            document_id="doc1",
            source_file="visual.pdf",
            page_number=1,
            text="diagram table",
            parent_text="diagram table",
            extraction_method="native",
            quality_score=1.0,
        ),
    )

    visual = visual_for_hit(hit)
    image_path = render_page_image("doc1", 1)

    assert visual is not None
    assert visual.url == "/api/pages/doc1/1/image"
    assert image_path.exists()
    assert image_path.suffix == ".png"
