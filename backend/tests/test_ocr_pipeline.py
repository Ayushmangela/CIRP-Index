import io
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

import httpx
import pytest
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from ingestion.ocr_pipeline import OcrError, ocr_pdf, process_order
from ingestion.pdf_pipeline import RateLimitedDownloader
from models.enums import ProcessingStatusEnum
from models.order import Order, OrderPage


def _blank_pdf_bytes(page_count: int) -> bytes:
    """A PDF with real pages but no text layer - stands in for a scanned
    order. pymupdf can rasterize it without any OCR involved; the OCR
    step itself is mocked in these tests so CI doesn't need tesseract."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(612, 792))
    for _ in range(page_count):
        c.showPage()
    c.save()
    return buffer.getvalue()


def _write_temp(content: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as f:
        f.write(content)
    return path


def _downloader_returning(content: bytes) -> RateLimitedDownloader:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=content)
    )
    downloader = RateLimitedDownloader("test@example.com")
    downloader._client = httpx.Client(transport=transport)
    return downloader


def _make_order(db: Session, pdf_url: str) -> Order:
    order = Order(
        subject_raw="In the matter of Test Co [CP (IB) 1/AB/2024]",
        pdf_url=pdf_url,
        processing_status=ProcessingStatusEnum.scanned_skipped,
        is_scanned=True,
        retrieved_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()
    return order


class TestOcrPdf:
    def test_ocrs_each_page_with_mocked_tesseract(self) -> None:
        pdf_bytes = _blank_pdf_bytes(2)
        path = _write_temp(pdf_bytes)
        try:
            with patch(
                "ingestion.ocr_pipeline.pytesseract.image_to_string",
                return_value="Recognised order text",
            ):
                result = ocr_pdf(path)
            assert result.page_count == 2
            assert all("Recognised order text" in p for p in result.pages)
        finally:
            os.unlink(path)

    def test_unreadable_pdf_raises_ocr_error(self) -> None:
        path = _write_temp(b"not a pdf at all")
        try:
            with pytest.raises(OcrError, match="unreadable pdf"):
                ocr_pdf(path)
        finally:
            os.unlink(path)


class TestProcessOrder:
    def test_successful_ocr_creates_order_pages(self, db_session: Session) -> None:
        order = _make_order(db_session, "https://ibbi.gov.in/uploads/order/a.pdf")
        pdf_bytes = _blank_pdf_bytes(2)
        downloader = _downloader_returning(pdf_bytes)

        with patch(
            "ingestion.ocr_pipeline.pytesseract.image_to_string",
            return_value="This is enough recognised text to clear the "
            "minimum-characters-per-page threshold for a real order page.",
        ):
            outcome = process_order(order, downloader, db_session)
        db_session.flush()

        assert outcome == "ocr_extracted"
        assert order.processing_status == ProcessingStatusEnum.ocr_extracted
        assert order.page_count == 2

        pages = (
            db_session.query(OrderPage)
            .filter(OrderPage.order_id == order.id)
            .order_by(OrderPage.page_number)
            .all()
        )
        assert len(pages) == 2
        assert "recognised text" in pages[0].text

    def test_near_empty_ocr_leaves_order_scanned_skipped(
        self, db_session: Session
    ) -> None:
        order = _make_order(db_session, "https://ibbi.gov.in/uploads/order/b.pdf")
        pdf_bytes = _blank_pdf_bytes(1)
        downloader = _downloader_returning(pdf_bytes)

        with patch(
            "ingestion.ocr_pipeline.pytesseract.image_to_string", return_value=""
        ):
            outcome = process_order(order, downloader, db_session)
        db_session.flush()

        assert outcome == "ocr_empty"
        assert order.processing_status == ProcessingStatusEnum.scanned_skipped

        pages = db_session.query(OrderPage).filter(OrderPage.order_id == order.id).all()
        assert len(pages) == 0

    def test_download_failure_is_reported_and_status_untouched(
        self, db_session: Session
    ) -> None:
        order = _make_order(db_session, "https://ibbi.gov.in/uploads/order/c.pdf")
        transport = httpx.MockTransport(lambda request: httpx.Response(404))
        downloader = RateLimitedDownloader("test@example.com")
        downloader._client = httpx.Client(transport=transport)

        outcome = process_order(order, downloader, db_session)

        assert outcome == "404"
        assert order.processing_status == ProcessingStatusEnum.scanned_skipped
