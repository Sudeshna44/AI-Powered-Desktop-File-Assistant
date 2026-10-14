import unittest
from unittest.mock import patch

import requests

from ollama_client import DEFAULT_OPTIONS, build_messages, generate_response


class BuildMessagesTests(unittest.TestCase):
    def test_prompt_contains_document_request_and_grounding_instructions(self):
        messages = build_messages("Quarterly revenue increased.", "What increased?")

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("Do not invent facts", messages[0]["content"])
        self.assertIn("Quarterly revenue increased.", messages[1]["content"])
        self.assertIn("What increased?", messages[1]["content"])

    @patch("ollama_client.requests.post")
    def test_uses_reduced_memory_options(self, post):
        post.return_value.ok = True
        post.return_value.json.return_value = {
            "message": {"content": "Revenue increased."}
        }

        result = generate_response("Document text", "Question?")

        self.assertEqual(result, "Revenue increased.")
        self.assertEqual(post.call_args.kwargs["json"]["options"], DEFAULT_OPTIONS)
        self.assertEqual(DEFAULT_OPTIONS, {"num_ctx": 1024, "num_batch": 64})

    @patch("ollama_client.requests.post", side_effect=requests.ConnectionError)
    def test_reports_when_ollama_is_not_running(self, _post):
        with self.assertRaisesRegex(RuntimeError, "Make sure Ollama is running"):
            generate_response("Document text", "Question?")

    @patch("ollama_client.requests.post")
    def test_reports_actionable_memory_error(self, post):
        post.return_value.ok = False
        post.return_value.status_code = 500
        post.return_value.text = '{"error":"failed to allocate CPU buffer"}'

        with self.assertRaisesRegex(RuntimeError, "ollama pull llama3.2:1b"):
            generate_response("Document text", "Question?")
