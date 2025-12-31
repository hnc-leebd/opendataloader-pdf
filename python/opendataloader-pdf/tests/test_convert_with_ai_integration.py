"""Integration tests for convert_with_ai (slow, requires docling)."""

import json
import tempfile
from pathlib import Path

import pytest

import opendataloader_pdf
from opendataloader_pdf.hybrid import HybridPipelineConfig


@pytest.fixture(scope="module")
def hybrid_result(input_pdf, module_output_dir):
    """Run convert_with_ai once and share result across tests."""
    hybrid_dir = module_output_dir / "hybrid"
    hybrid_dir.mkdir(exist_ok=True)

    config = HybridPipelineConfig(keep_intermediate=True)
    result = opendataloader_pdf.convert_with_ai(
        input_path=str(input_pdf),
        output_dir=str(hybrid_dir),
        config=config,
    )
    return {"result": result, "output_dir": hybrid_dir}


class TestConvertWithAiIntegration:
    """Integration tests for convert_with_ai function."""

    def test_returns_valid_dict(self, hybrid_result):
        """Verify convert_with_ai returns a valid dictionary with required fields."""
        result = hybrid_result["result"]

        assert isinstance(result, dict)
        assert "number of pages" in result
        assert "kids" in result
        assert result["number of pages"] > 0
        assert len(result["kids"]) > 0

    def test_generates_output_files(self, hybrid_result):
        """Verify all expected output files are generated."""
        output_dir = hybrid_result["output_dir"]

        # Main JSON output
        json_output = output_dir / "1901.03003.json"
        assert json_output.exists(), f"JSON output not found at {json_output}"
        assert json_output.stat().st_size > 0

        # Triage JSON
        triage_output = output_dir / "triage.json"
        assert triage_output.exists()
        with open(triage_output) as f:
            triage = json.load(f)
        assert "pages" in triage
        for page in triage["pages"]:
            assert page["path"] in ("fast", "ai")

        # Fast pages JSON
        fast_pages_output = output_dir / "fast_pages.json"
        assert fast_pages_output.exists()

        # AI page images (if any AI pages)
        ai_pages_dir = output_dir / "ai_pages"
        if ai_pages_dir.exists():
            png_files = list(ai_pages_dir.glob("*.png"))
            assert all(f.name.startswith("page_") for f in png_files)

    def test_extracts_content_from_all_pages(self, hybrid_result):
        """Verify content extraction coverage across pages."""
        result = hybrid_result["result"]
        num_pages = result["number of pages"]

        pages_with_content = {kid.get("page number") for kid in result["kids"] if kid.get("page number")}

        assert len(pages_with_content) >= num_pages * 0.8, (
            f"Expected 80%+ page coverage, got {len(pages_with_content)}/{num_pages}"
        )

    def test_json_schema_compliance(self, hybrid_result):
        """Verify output conforms to OpenDataLoader JSON schema."""
        result = hybrid_result["result"]

        # Root fields
        assert "file name" in result or "file_name" in result
        assert "number of pages" in result or "number_of_pages" in result
        assert "kids" in result

        # Element structure
        for kid in result["kids"][:10]:
            assert "type" in kid
            assert "page number" in kid or "page_number" in kid

            if kid.get("type") in ("paragraph", "heading", "caption", "list item"):
                assert "content" in kid


class TestConvertWithAiOutputFormats:
    """Test convert_with_ai output format generation."""

    @pytest.fixture
    def input_pdf(self):
        """Get path to test PDF."""
        pdf_path = Path(__file__).resolve().parents[3] / "samples" / "pdf" / "1901.03003.pdf"
        if not pdf_path.exists():
            pytest.skip("Test PDF not found")
        return pdf_path

    def test_json_format_output(self, input_pdf):
        """Test that JSON format generates expected output files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            config = HybridPipelineConfig(keep_intermediate=True)

            result = opendataloader_pdf.convert_with_ai(
                input_path=str(input_pdf),
                output_dir=str(output_dir),
                format="json",
                config=config,
            )

            # Verify JSON result is returned
            assert isinstance(result, dict)
            assert "number of pages" in result
            assert "kids" in result

            # Verify JSON file is created
            json_output = output_dir / f"{input_pdf.stem}.json"
            assert json_output.exists(), f"JSON output not found at {json_output}"

            with open(json_output) as f:
                saved_result = json.load(f)
            assert saved_result["number of pages"] == result["number of pages"]

    def test_markdown_format_output(self, input_pdf):
        """Test that markdown format generates .md files for AI pages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            config = HybridPipelineConfig(keep_intermediate=True)

            opendataloader_pdf.convert_with_ai(
                input_path=str(input_pdf),
                output_dir=str(output_dir),
                format="markdown",
                config=config,
            )

            # Check for AI pages markdown output
            ai_pages_dir = output_dir / "ai_pages"
            if ai_pages_dir.exists():
                md_files = list(ai_pages_dir.glob("*.md"))
                # If there are AI pages, markdown files should be generated
                for md_file in md_files:
                    assert md_file.stat().st_size > 0, f"Markdown file {md_file} is empty"
                    content = md_file.read_text(encoding="utf-8")
                    assert len(content) > 0

    def test_html_format_output(self, input_pdf):
        """Test that HTML format generates .html files for AI pages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            config = HybridPipelineConfig(keep_intermediate=True)

            opendataloader_pdf.convert_with_ai(
                input_path=str(input_pdf),
                output_dir=str(output_dir),
                format="html",
                config=config,
            )

            # Check for AI pages HTML output
            ai_pages_dir = output_dir / "ai_pages"
            if ai_pages_dir.exists():
                html_files = list(ai_pages_dir.glob("*.html"))
                for html_file in html_files:
                    assert html_file.stat().st_size > 0, f"HTML file {html_file} is empty"
                    content = html_file.read_text(encoding="utf-8")
                    assert len(content) > 0

    def test_text_format_output(self, input_pdf):
        """Test that text format generates .txt files for AI pages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            config = HybridPipelineConfig(keep_intermediate=True)

            opendataloader_pdf.convert_with_ai(
                input_path=str(input_pdf),
                output_dir=str(output_dir),
                format="text",
                config=config,
            )

            # Check for AI pages text output
            ai_pages_dir = output_dir / "ai_pages"
            if ai_pages_dir.exists():
                txt_files = list(ai_pages_dir.glob("*.txt"))
                for txt_file in txt_files:
                    assert txt_file.stat().st_size > 0, f"Text file {txt_file} is empty"

    def test_multiple_formats_output(self, input_pdf):
        """Test that multiple formats can be specified together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            config = HybridPipelineConfig(keep_intermediate=True)

            result = opendataloader_pdf.convert_with_ai(
                input_path=str(input_pdf),
                output_dir=str(output_dir),
                format=["json", "markdown", "html"],
                config=config,
            )

            # Verify JSON result is returned
            assert isinstance(result, dict)

            # Verify JSON file is created
            json_output = output_dir / f"{input_pdf.stem}.json"
            assert json_output.exists()

            # Check for AI pages with multiple formats
            ai_pages_dir = output_dir / "ai_pages"
            if ai_pages_dir.exists():
                md_files = list(ai_pages_dir.glob("*.md"))
                html_files = list(ai_pages_dir.glob("*.html"))
                # Both formats should be generated for each AI page
                if md_files:
                    assert len(html_files) == len(md_files), (
                        f"Expected same number of HTML and MD files, "
                        f"got {len(html_files)} HTML and {len(md_files)} MD"
                    )

    def test_format_files_contain_valid_content(self, input_pdf):
        """Test that generated format files contain valid content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            config = HybridPipelineConfig(keep_intermediate=True)

            opendataloader_pdf.convert_with_ai(
                input_path=str(input_pdf),
                output_dir=str(output_dir),
                format=["markdown", "html"],
                config=config,
            )

            ai_pages_dir = output_dir / "ai_pages"
            if ai_pages_dir.exists():
                # Validate markdown content
                for md_file in ai_pages_dir.glob("*.md"):
                    content = md_file.read_text(encoding="utf-8")
                    # Markdown should not be empty
                    assert len(content.strip()) > 0, f"Empty markdown in {md_file}"

                # Validate HTML content
                for html_file in ai_pages_dir.glob("*.html"):
                    content = html_file.read_text(encoding="utf-8")
                    # HTML should contain basic structure
                    assert len(content.strip()) > 0, f"Empty HTML in {html_file}"
