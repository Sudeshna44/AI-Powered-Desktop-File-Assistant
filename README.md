# SmartDesk AI – Local File Assistant

A Windows desktop application for asking questions about local TXT and PDF
documents. It uses Tkinter for the interface and Ollama for local inference;
document text is sent only to the Ollama server running on your computer.

## Requirements

- Python 3.10 or newer
- [Ollama for Windows](https://ollama.com/download)
- The `llama3.2` Ollama model

## Setup

1. Install Ollama, then open PowerShell or Command Prompt and run:

   ```powershell
   ollama pull llama3.2
   ```

2. From this project directory, install the Python dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Start Ollama if it is not already running, then launch SmartDesk AI:

   ```powershell
   python app.py
   ```

## Use

Choose a `.txt` or `.pdf` file, enter a question, and select **Ask** (or press
Enter). Select **Summarize** for a concise summary. Use **Save conversation**
to save the current questions and answers as a local text file.

PDF text extraction does not perform OCR; scanned or image-only PDFs need to
be converted to searchable text before they can be used. Very large documents
may exceed the context capacity configured for the selected Ollama model.

If Ollama is unavailable, SmartDesk AI displays an error and suggests starting
the local server. If `llama3.2` is missing, run `ollama pull llama3.2`.

### If Ollama runs out of memory

SmartDesk AI requests a smaller context and batch size to reduce Ollama's memory
use. If the model still cannot start, close other memory-intensive apps. On
low-memory PCs, install the smaller Llama 3.2 1B model:

```powershell
ollama pull llama3.2:1b
$env:SMARTDESK_MODEL = "llama3.2:1b"
.\.venv\Scripts\python.exe app.py
```

The model selection applies to that PowerShell session. The 1B model is smaller
but may provide less capable answers than the default 3B model.
