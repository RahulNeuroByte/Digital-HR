"""
PDF Generation Utility for Digital HR.

Generates clean, professional enterprise PDF exports from chat responses
using fpdf2. Contains zero internal debug metadata.
"""
from __future__ import annotations

import re
from datetime import datetime
from fpdf import FPDF


class EnterprisePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(23, 32, 51)  # #172033
        self.cell(0, 10, "Coforge  |  Digital-HR Policy Desk", border=0, new_x="RIGHT", new_y="TOP", align="L")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 116, 139)  # #64748B
        self.cell(0, 10, f"Generated: {datetime.now().strftime('%d %b %Y')}", border=0, new_x="LMARGIN", new_y="NEXT", align="R")
        self.set_draw_color(226, 232, 240)
        self.line(10, 20, 200, 20)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, "Official Coforge HR-India Policy Document  |  Internal Use Only", border=0, new_x="RIGHT", new_y="TOP", align="L")
        self.cell(0, 10, f"Page {self.page_no()}", border=0, new_x="LMARGIN", new_y="NEXT", align="R")


def clean_markdown_for_pdf(text: str) -> str:
    """Strip markdown formatting and non-latin1 characters for clean PDF rendering."""
    # Replace common unicode chars with ascii approximations
    text = text.replace("•", "-").replace("—", "-").replace("–", "-").replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"#(.*?)\n", r"\1\n", text)
    text = text.replace("`", "")
    return text


def generate_answer_pdf(title: str, content: str, policy_name: str | None = None) -> bytes:
    """
    Generate downloadable PDF document bytes for a given answer.
    """
    pdf = EnterprisePDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(15, 23, 42)
    clean_title = clean_markdown_for_pdf(title)
    pdf.multi_cell(0, 8, clean_title)
    pdf.ln(2)

    # Subtitle / Policy tag
    if policy_name:
        clean_pol = clean_markdown_for_pdf(policy_name)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(37, 99, 235)  # #2563EB
        pdf.cell(0, 6, f"Policy Focus: {clean_pol}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # Content body
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)

    clean_body = clean_markdown_for_pdf(content)
    lines = clean_body.split("\n")

    for line in lines:
        line_str = line.strip()
        if not line_str:
            pdf.ln(4)
            continue
        
        # Heading-like line
        if line_str.endswith(":") and len(line_str) < 60:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(15, 23, 42)
            pdf.multi_cell(0, 6, line_str)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(51, 65, 85)
        # Bullet list item
        elif line_str.startswith("- ") or line_str.startswith("* ") or re.match(r"^\d+\.", line_str):
            pdf.multi_cell(0, 5, f"  {line_str}")
        else:
            pdf.multi_cell(0, 5, line_str)

    return bytes(pdf.output())
