"""Document loading helpers for SmartDesk AI."""

from pathlib import Path

try:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError
except ImportError:  # pragma: no cover - exercised when dependencies are missing.
    PdfReader = None  # type: ignore[assignment]
    PdfReadError = ValueError  # type: ignore[assignment]


SUPPORTED_EXTENSIONS = {".txt", ".pdf"}


def load_document(path: str | Path) -> str:
    """Read a supported text or PDF document and return its extracted text."""
    document_path = Path(path)
    extension = document_path.suffix.lower()

    if extension == ".txt":
        text = document_path.read_text(encoding="utf-8-sig")
    elif extension == ".pdf":
        if PdfReader is None:
            raise ValueError(
                "PDF support requires the 'pypdf' package. Install project dependencies with: "
                "python -m pip install -r requirements.txt"
            )
        try:
            reader = PdfReader(str(document_path))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except PdfReadError as exc:
            raise ValueError(f"Could not read PDF: {exc}") from exc
    else:
        raise ValueError("Unsupported file type. Please select a TXT or PDF file.")

    text = text.strip()
    if not text:
        raise ValueError(
            "No readable text was found. The document may be empty, scanned, or image-only."
        )
    return text
