"""Small synchronous Ollama API client; call it from a worker thread."""

import os

try:
    import requests
except ImportError:  # pragma: no cover - exercised when dependencies are missing.
    requests = None  # type: ignore[assignment]


DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = os.environ.get("SMARTDESK_MODEL", "llama3.2")
DEFAULT_OPTIONS = {"num_ctx": 1024, "num_batch": 64}


def build_messages(document_text: str, prompt: str) -> list[dict[str, str]]:
    """Build a grounded prompt for a document question or summary."""
    return [
        {
            "role": "system",
            "content": (
                "You are SmartDesk AI, a private local document assistant. "
                "Answer using only the supplied document. If the document does not "
                "contain the answer, say so clearly. Do not invent facts."
            ),
        },
        {
            "role": "user",
            "content": f"DOCUMENT:\n{document_text}\n\nREQUEST:\n{prompt}",
        },
    ]


def generate_response(
    document_text: str,
    prompt: str,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
) -> str:
    """Request a non-streaming response from the local Ollama server."""
    if requests is None:
        raise RuntimeError(
            "The 'requests' package is missing. Install project dependencies with: "
            "python -m pip install -r requirements.txt"
        )

    url = f"{base_url.rstrip('/')}/api/chat"
    try:
        response = requests.post(
            url,
            json={
                "model": model,
                "messages": build_messages(document_text, prompt),
                "stream": False,
                "options": DEFAULT_OPTIONS,
            },
            timeout=(5, 300),
        )
    except requests.ConnectionError as exc:
        raise RuntimeError(
            "Could not connect to Ollama. Make sure Ollama is running, then try again."
        ) from exc
    except requests.Timeout as exc:
        raise RuntimeError("Ollama took too long to respond. Please try again.") from exc
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not contact Ollama: {exc}") from exc

    if response.status_code == 404:
        raise RuntimeError(
            f"The model '{model}' is not available. In a terminal, run: ollama pull {model}"
        )
    if not response.ok:
        detail = response.text.strip()
        if "out of memory" in detail.lower() or "failed to allocate" in detail.lower():
            raise RuntimeError(
                "Ollama ran out of memory while starting the model. Close other apps "
                "and try again. This computer has limited RAM; a smaller model may "
                "work better. To use Llama 3.2 1B, run `ollama pull llama3.2:1b`, "
                "then set `$env:SMARTDESK_MODEL='llama3.2:1b'` in PowerShell before "
                "launching SmartDesk AI."
            )
        raise RuntimeError(
            f"Ollama returned HTTP {response.status_code}"
            + (f": {detail}" if detail else ".")
        )

    try:
        result = response.json()
        answer = result["message"]["content"].strip()
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError("Ollama returned an invalid response.") from exc

    if not answer:
        raise RuntimeError("Ollama returned an empty response.")
    return answer
