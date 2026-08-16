"""Unit tests for PDF Generation utility."""
import pytest
from app.utils.pdf_generator import generate_answer_pdf


def test_generate_answer_pdf_returns_bytes():
    title = "Leave Policy Overview"
    content = "You are entitled to 24 days of leave per year. Submit applications via iEngage portal."
    pdf_bytes = generate_answer_pdf(title, content, policy_name="Leave Policy")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")
