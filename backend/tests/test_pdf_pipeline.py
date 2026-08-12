import io
import os
import tempfile
from datetime import datetime, timezone

import httpx
import pytest
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from ingestion.pdf_pipeline import (
    PdfDownloadError,
    RateLimitedDownloader,
    _check_not_encrypted,
    _normalise_page_text,
    extract_text,
    process_order,
)
from models.enums import ProcessingStatusEnum
from models.order import Order, OrderPage


def _text_pdf_bytes(pages: list[str]) -> bytes:
    """Build a PDF with real, extractable text - each page repeats its
    marker text across several lines so the total exceeds the pipeline's
    100-chars/page scanned-detection threshold, like a real order page."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(612, 792))
    for text in pages:
        y = 720
        for _ in range(10):
            c.drawString(72, y, text)
            y -= 20
        c.showPage()
    c.save()
    return buffer.getvalue()


def _blank_pdf_bytes(page_count: int) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(612, 792))
    for _ in range(page_count):
        c.showPage()
    c.save()
    return buffer.getvalue()


def _encrypted_pdf_bytes(pages: list[str], password: str) -> bytes:
    plain = _text_pdf_bytes(pages)
    reader = PdfReader(io.BytesIO(plain))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=password)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


class TestNormalisePageText:
    def test_collapses_repeated_spaces_and_tabs(self) -> None:
        assert _normalise_page_text("a   b\t\tc") == "a b c"

    def test_preserves_line_breaks(self) -> None:
        assert _normalise_page_text("line one\nline two") == "line one\nline two"

    def test_strips_trailing_whitespace_per_line(self) -> None:
        assert _normalise_page_text("line one   \n  line two") == "line one\nline two"


class TestExtractText:
    def test_digital_pdf_extracts_readable_pages(self) -> None:
        pdf_bytes = _text_pdf_bytes(["Page one content", "Page two content"])
        path = _write_temp(pdf_bytes)
        try:
            result = extract_text(path)
            assert result.page_count == 2
            assert result.is_scanned is False
            assert "Page one content" in result.pages[0]
            assert "Page two content" in result.pages[1]
        finally:
            os.unlink(path)

    def test_blank_pages_are_flagged_as_scanned(self) -> None:
        pdf_bytes = _blank_pdf_bytes(3)
        path = _write_temp(pdf_bytes)
        try:
            result = extract_text(path)
            assert result.page_count == 3
            assert result.is_scanned is True
        finally:
            os.unlink(path)


class TestEncryptionCheck:
    def test_encrypted_pdf_raises(self) -> None:
        pdf_bytes = _encrypted_pdf_bytes(["secret content"], password="hunter2")
        path = _write_temp(pdf_bytes)
        try:
            with pytest.raises(PdfDownloadError, match="password-protected"):
                _check_not_encrypted(path)
        finally:
            os.unlink(path)

    def test_unencrypted_pdf_does_not_raise(self) -> None:
        pdf_bytes = _text_pdf_bytes(["not secret"])
        path = _write_temp(pdf_bytes)
        try:
            _check_not_encrypted(path)
        finally:
            os.unlink(path)


class TestRateLimitedDownloaderErrors:
    def test_404_raises_with_reason(self) -> None:
        transport = httpx.MockTransport(lambda request: httpx.Response(404))
        downloader = _downloader_with_transport(transport)
        with pytest.raises(PdfDownloadError, match="404"):
            downloader.download("https://ibbi.gov.in/uploads/order/missing.pdf")

    def test_server_error_raises(self) -> None:
        transport = httpx.MockTransport(lambda request: httpx.Response(500))
        downloader = _downloader_with_transport(transport)
        with pytest.raises(PdfDownloadError, match="http 500"):
            downloader.download("https://ibbi.gov.in/uploads/order/x.pdf")

    def test_zero_byte_response_raises(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"")
        )
        downloader = _downloader_with_transport(transport)
        with pytest.raises(PdfDownloadError, match="zero-byte"):
            downloader.download("https://ibbi.gov.in/uploads/order/x.pdf")

    def test_html_error_page_at_pdf_url_raises(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"<html>Error</html>")
        )
        downloader = _downloader_with_transport(transport)
        with pytest.raises(PdfDownloadError, match="not a pdf"):
            downloader.download("https://ibbi.gov.in/uploads/order/x.pdf")

    def test_timeout_raises(self) -> None:
        def raise_timeout(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timed out", request=request)

        transport = httpx.MockTransport(raise_timeout)
        downloader = _downloader_with_transport(transport)
        with pytest.raises(PdfDownloadError, match="timeout"):
            downloader.download("https://ibbi.gov.in/uploads/order/x.pdf")

    def test_valid_pdf_returns_bytes(self) -> None:
        pdf_bytes = _text_pdf_bytes(["hello"])
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=pdf_bytes)
        )
        downloader = _downloader_with_transport(transport)
        result = downloader.download("https://ibbi.gov.in/uploads/order/x.pdf")
        assert result == pdf_bytes


class TestProcessOrder:
    def test_digital_pdf_creates_order_pages(self, db_session: Session) -> None:
        order = _make_order(db_session, "https://ibbi.gov.in/uploads/order/a.pdf")
        pdf_bytes = _text_pdf_bytes(["Order text page one", "Order text page two"])
        downloader = _downloader_returning(pdf_bytes)

        outcome = process_order(order, downloader, db_session)
        db_session.flush()

        assert outcome == "text_extracted"
        assert order.processing_status == ProcessingStatusEnum.text_extracted
        assert order.is_scanned is False
        assert order.page_count == 2
        assert order.pdf_sha256 is not None

        pages = (
            db_session.query(OrderPage)
            .filter(OrderPage.order_id == order.id)
            .order_by(OrderPage.page_number)
            .all()
        )
        assert len(pages) == 2
        assert "Order text page one" in pages[0].text

    def test_scanned_pdf_skips_page_storage(self, db_session: Session) -> None:
        order = _make_order(db_session, "https://ibbi.gov.in/uploads/order/b.pdf")
        pdf_bytes = _blank_pdf_bytes(2)
        downloader = _downloader_returning(pdf_bytes)

        outcome = process_order(order, downloader, db_session)
        db_session.flush()

        assert outcome == "scanned"
        assert order.processing_status == ProcessingStatusEnum.scanned_skipped
        assert order.is_scanned is True

        pages = db_session.query(OrderPage).filter(OrderPage.order_id == order.id).all()
        assert len(pages) == 0

    def test_encrypted_pdf_marked_failed(self, db_session: Session) -> None:
        order = _make_order(db_session, "https://ibbi.gov.in/uploads/order/c.pdf")
        pdf_bytes = _encrypted_pdf_bytes(["secret"], password="hunter2")
        downloader = _downloader_returning(pdf_bytes)

        outcome = process_order(order, downloader, db_session)

        assert outcome == "password-protected"
        assert order.processing_status == ProcessingStatusEnum.failed

    def test_404_marked_failed_without_touching_hash(self, db_session: Session) -> None:
        order = _make_order(db_session, "https://ibbi.gov.in/uploads/order/d.pdf")
        transport = httpx.MockTransport(lambda request: httpx.Response(404))
        downloader = _downloader_with_transport(transport)

        outcome = process_order(order, downloader, db_session)

        assert outcome == "404"
        assert order.processing_status == ProcessingStatusEnum.failed
        assert order.pdf_sha256 is None

    def test_duplicate_content_copies_pages_without_reparsing(
        self, db_session: Session
    ) -> None:
        pdf_bytes = _text_pdf_bytes(["shared content"])

        original = _make_order(db_session, "https://ibbi.gov.in/uploads/order/orig.pdf")
        process_order(original, _downloader_returning(pdf_bytes), db_session)
        db_session.flush()

        duplicate = _make_order(
            db_session, "https://ibbi.gov.in/uploads/order/dupe.pdf"
        )
        outcome = process_order(duplicate, _downloader_returning(pdf_bytes), db_session)
        db_session.flush()

        assert outcome == "duplicate_content"
        assert duplicate.processing_status == ProcessingStatusEnum.text_extracted
        assert duplicate.pdf_sha256 == original.pdf_sha256

        dup_pages = (
            db_session.query(OrderPage).filter(OrderPage.order_id == duplicate.id).all()
        )
        assert len(dup_pages) == 1
        assert "shared content" in dup_pages[0].text


def _write_temp(content: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, "wb") as f:
        f.write(content)
    return path


def _downloader_with_transport(transport: httpx.MockTransport) -> RateLimitedDownloader:
    downloader = RateLimitedDownloader("test@example.com")
    downloader._client = httpx.Client(transport=transport)
    return downloader


def _downloader_returning(content: bytes) -> RateLimitedDownloader:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=content)
    )
    return _downloader_with_transport(transport)


def _make_order(db: Session, pdf_url: str) -> Order:
    order = Order(
        subject_raw="In the matter of Test Co [CP (IB) 1/AB/2024]",
        pdf_url=pdf_url,
        processing_status=ProcessingStatusEnum.discovered,
        retrieved_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.flush()
    return order
