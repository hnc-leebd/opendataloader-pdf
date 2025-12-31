"""Integration tests that actually run the JAR (slow)"""

import opendataloader_pdf


def test_convert_generates_json_output(input_pdf, output_dir):
    """Verify that convert() generates JSON output files."""
    opendataloader_pdf.convert(
        input_path=str(input_pdf),
        output_dir=str(output_dir),
        format="json",
        quiet=True,
    )
    output = output_dir / "1901.03003.json"
    assert output.exists(), f"JSON output file not found at {output}"
    assert output.stat().st_size > 0, "JSON output file is empty"


def test_convert_generates_markdown_output(input_pdf, output_dir):
    """Verify that convert() generates Markdown output files."""
    opendataloader_pdf.convert(
        input_path=str(input_pdf),
        output_dir=str(output_dir),
        format="markdown",
        quiet=True,
    )
    output = output_dir / "1901.03003.md"
    assert output.exists(), f"Markdown output file not found at {output}"
    assert output.stat().st_size > 0, "Markdown output file is empty"

    # Verify content has markdown structure
    with open(output) as f:
        content = f.read()
    assert len(content) > 100, "Markdown content is too short"


def test_convert_generates_html_output(input_pdf, output_dir):
    """Verify that convert() generates HTML output files."""
    opendataloader_pdf.convert(
        input_path=str(input_pdf),
        output_dir=str(output_dir),
        format="html",
        quiet=True,
    )
    output = output_dir / "1901.03003.html"
    assert output.exists(), f"HTML output file not found at {output}"
    assert output.stat().st_size > 0, "HTML output file is empty"

    # Verify content is valid HTML
    with open(output) as f:
        content = f.read()
    assert "<html" in content.lower(), "HTML output missing <html> tag"
    assert "</html>" in content.lower(), "HTML output missing </html> tag"


def test_convert_generates_multiple_formats(input_pdf, output_dir):
    """Verify that convert() can generate multiple output formats at once."""
    opendataloader_pdf.convert(
        input_path=str(input_pdf),
        output_dir=str(output_dir),
        format=["json", "markdown", "html"],
        quiet=True,
    )

    json_output = output_dir / "1901.03003.json"
    md_output = output_dir / "1901.03003.md"
    html_output = output_dir / "1901.03003.html"

    assert json_output.exists(), f"JSON output file not found at {json_output}"
    assert md_output.exists(), f"Markdown output file not found at {md_output}"
    assert html_output.exists(), f"HTML output file not found at {html_output}"

    assert json_output.stat().st_size > 0, "JSON output file is empty"
    assert md_output.stat().st_size > 0, "Markdown output file is empty"
    assert html_output.stat().st_size > 0, "HTML output file is empty"
