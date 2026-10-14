import tempfile
import unittest
from pathlib import Path

from document_utils import load_document


class LoadDocumentTests(unittest.TestCase):
    def test_loads_utf8_text_with_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.txt"
            path.write_text("\ufeffLocal document text", encoding="utf-8")

            self.assertEqual(load_document(path), "Local document text")

    def test_rejects_empty_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.txt"
            path.write_text("  \n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "No readable text"):
                load_document(path)

    def test_rejects_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.docx"
            path.write_text("not a supported document", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Unsupported file type"):
                load_document(path)
