#!/usr/bin/env python3
"""Convert markdown to PDF using markdown2 and reportlab."""

from pathlib import Path
import subprocess

MD_FILE = Path("/Users/darwin.minota.quinto/Projects/NEXA/backend_nexa/deliverables/NEXA_Architecture_Complete.md")
PDF_FILE = Path("/Users/darwin.minota.quinto/Projects/NEXA/backend_nexa/deliverables/NEXA_Architecture_Updated.pdf")

def convert_md_to_pdf():
    """Convert using system tools."""

    # Try using wkhtmltopdf or similar
    commands = [
        # Try libreoffice (if available)
        ["soffice", "--headless", "--convert-to", "pdf", str(MD_FILE), "--outdir", str(MD_FILE.parent)],

        # Try wkhtmltopdf via HTML conversion
        ["wkhtmltopdf", "-q", "/dev/stdin", str(PDF_FILE)],
    ]

    # As fallback, create a simple HTML -> PDF conversion
    try:
        from weasyprint import HTML, CSS

        # Read markdown
        with open(MD_FILE, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # Convert markdown to basic HTML
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>NEXA Architecture</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{ color: #1f4e79; margin-top: 30px; page-break-after: avoid; }}
        h2 {{ color: #4f81bd; margin-top: 20px; page-break-after: avoid; }}
        h3 {{ color: #5a6c7d; margin-top: 15px; page-break-after: avoid; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        th {{ background-color: #e8eef7; }}
        pre {{ background-color: #f5f5f5; padding: 10px; overflow-x: auto; }}
        code {{ font-family: 'Courier New', monospace; }}
        ul, ol {{ margin: 10px 0; }}
        li {{ margin: 5px 0; }}
        .page-break {{ page-break-after: always; }}
    </style>
</head>
<body>
{md_content}
</body>
</html>"""

        # Save HTML
        html_file = MD_FILE.parent / "NEXA_Architecture_temp.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Convert HTML to PDF
        HTML(str(html_file)).write_pdf(str(PDF_FILE))

        # Clean up
        html_file.unlink()

        print(f"✓ PDF created: {PDF_FILE}")
        return True

    except ImportError:
        print("WeasyPrint not available, trying alternative method...")

        # Try system command
        try:
            # Create simple HTML version for conversion
            import subprocess

            html_content = f"""<html>
<head><title>NEXA Architecture</title></head>
<body>
<pre>{md_content}</pre>
</body>
</html>"""

            html_file = MD_FILE.parent / "NEXA_Architecture_temp.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Try to use system utilities
            subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf",
                           "--outdir", str(MD_FILE.parent), str(html_file)],
                          check=False)

            html_file.unlink()

            if PDF_FILE.exists():
                print(f"✓ PDF created: {PDF_FILE}")
                return True
        except:
            pass

        return False

if __name__ == "__main__":
    try:
        if convert_md_to_pdf():
            print("\n✓ Conversion successful")
        else:
            print("\nNote: PDF conversion requires additional tools.")
            print("Install with: pip install weasyprint")
    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: PDF creation skipped. You can convert manually with:")
        print("  pandoc -f markdown -t pdf NEXA_Architecture_Complete.md -o NEXA_Architecture_Updated.pdf")
