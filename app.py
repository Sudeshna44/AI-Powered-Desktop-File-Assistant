"""SmartDesk AI — a local document assistant built with Tkinter."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from document_utils import load_document
from ollama_client import DEFAULT_MODEL, generate_response


class SmartDeskApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SmartDesk AI – Local File Assistant")
        self.root.geometry("980x700")
        self.root.minsize(760, 540)

        self.document_text: str | None = None
        self.document_path: Path | None = None
        self.conversation: list[tuple[str, str]] = []
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.busy = False

        self._configure_style()
        self._build_interface()
        self.root.after(100, self._process_events)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", foreground="#5f6b7a")
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))

    def _build_interface(self) -> None:
        container = ttk.Frame(self.root, padding=18)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 14))
        ttk.Label(header, text="SmartDesk AI", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            header,
            text="Ask questions about your files. Your documents stay on this computer.",
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(3, 0))

        document_bar = ttk.Frame(container)
        document_bar.pack(fill=tk.X, pady=(0, 12))
        self.open_button = ttk.Button(
            document_bar, text="Choose document", command=self._choose_document
        )
        self.open_button.pack(side=tk.LEFT)
        self.summarize_button = ttk.Button(
            document_bar,
            text="Summarize",
            command=self._summarize,
            state=tk.DISABLED,
        )
        self.summarize_button.pack(side=tk.LEFT, padx=(8, 0))
        self.save_button = ttk.Button(
            document_bar,
            text="Save conversation",
            command=self._save_conversation,
            state=tk.DISABLED,
        )
        self.save_button.pack(side=tk.RIGHT)

        self.document_label = ttk.Label(
            container, text="No document selected", style="Subtitle.TLabel"
        )
        self.document_label.pack(fill=tk.X, pady=(0, 10))

        chat_frame = ttk.Frame(container)
        chat_frame.pack(fill=tk.BOTH, expand=True)
        self.chat = tk.Text(
            chat_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            padx=14,
            pady=12,
            font=("Segoe UI", 10),
            background="#f7f9fc",
            relief=tk.FLAT,
        )
        scrollbar = ttk.Scrollbar(chat_frame, orient=tk.VERTICAL, command=self.chat.yview)
        self.chat.configure(yscrollcommand=scrollbar.set)
        self.chat.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat.tag_configure("user", foreground="#155eef", font=("Segoe UI", 10, "bold"))
        self.chat.tag_configure("assistant", foreground="#1f2937")
        self.chat.tag_configure("error", foreground="#b42318")
        self._append_chat(
            "SmartDesk AI",
            "Choose a TXT or PDF document to get started. Questions are answered "
            "by Ollama running locally on your computer.",
            "assistant",
        )

        entry_frame = ttk.Frame(container)
        entry_frame.pack(fill=tk.X, pady=(12, 0))
        self.question_entry = ttk.Entry(entry_frame)
        self.question_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7)
        self.question_entry.bind("<Return>", self._on_enter)
        self.ask_button = ttk.Button(
            entry_frame,
            text="Ask",
            command=self._ask_question,
            style="Primary.TButton",
            state=tk.DISABLED,
        )
        self.ask_button.pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(value=f"Ready • Model: {DEFAULT_MODEL}")
        ttk.Label(container, textvariable=self.status_var, style="Subtitle.TLabel").pack(
            anchor=tk.W, pady=(9, 0)
        )

    def _append_chat(self, speaker: str, text: str, tag: str) -> None:
        self.chat.configure(state=tk.NORMAL)
        self.chat.insert(tk.END, f"{speaker}\n", tag)
        self.chat.insert(tk.END, f"{text}\n\n")
        self.chat.configure(state=tk.DISABLED)
        self.chat.see(tk.END)

    def _set_busy(self, busy: bool, status: str | None = None) -> None:
        self.busy = busy
        self.open_button.configure(state=tk.DISABLED if busy else tk.NORMAL)
        self.ask_button.configure(
            state=tk.NORMAL if not busy and self.document_text else tk.DISABLED
        )
        self.summarize_button.configure(
            state=tk.NORMAL if not busy and self.document_text else tk.DISABLED
        )
        self.save_button.configure(
            state=tk.NORMAL if not busy and self.conversation else tk.DISABLED
        )
        self.question_entry.configure(state=tk.DISABLED if busy else tk.NORMAL)
        if status:
            self.status_var.set(status)
        elif not busy:
            self.status_var.set(f"Ready • Model: {DEFAULT_MODEL}")

    def _choose_document(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select a document",
            filetypes=[
                ("Supported documents", "*.txt *.pdf"),
                ("Text files", "*.txt"),
                ("PDF files", "*.pdf"),
            ],
        )
        if not selected:
            return

        path = Path(selected)
        self.document_label.configure(text=f"Loading {path.name}…")
        self._set_busy(True, "Reading document…")
        threading.Thread(
            target=self._load_document_worker,
            args=(path,),
            daemon=True,
        ).start()

    def _load_document_worker(self, path: Path) -> None:
        try:
            text = load_document(path)
            self.events.put(("document_loaded", (path, text)))
        except (OSError, ValueError) as exc:
            self.events.put(("error", f"Could not read the document:\n{exc}"))

    def _ask_question(self) -> None:
        question = self.question_entry.get().strip()
        if self.busy:
            return
        if not self.document_text:
            messagebox.showinfo("Select a document", "Choose a document before asking a question.")
            return
        if not question:
            self.question_entry.focus_set()
            return

        self.question_entry.delete(0, tk.END)
        self.conversation.append((question, ""))
        self._append_chat("You", question, "user")
        self._start_generation(question, question)

    def _summarize(self) -> None:
        if self.busy or not self.document_text:
            return
        prompt = (
            "Summarize this document. Identify its main purpose, key points, and "
            "important conclusions. Use clear, concise bullet points."
        )
        self.conversation.append(("Summarize document", ""))
        self._append_chat("You", "Summarize this document.", "user")
        self._start_generation(prompt, "Summarizing document…")

    def _start_generation(self, prompt: str, status: str) -> None:
        document = self.document_text
        if document is None:
            return
        self._set_busy(True, status)
        threading.Thread(
            target=self._generation_worker,
            args=(document, prompt),
            daemon=True,
        ).start()

    def _generation_worker(self, document: str, prompt: str) -> None:
        try:
            answer = generate_response(document, prompt)
            self.events.put(("answer", answer))
        except RuntimeError as exc:
            self.events.put(("error", str(exc)))

    def _process_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "document_loaded":
                    path, text = value
                    self.document_path = path
                    self.document_text = text
                    self.document_label.configure(
                        text=f"Selected: {path.name}  •  {len(text):,} characters"
                    )
                    self._append_chat(
                        "SmartDesk AI",
                        f"Loaded {path.name}. Ask a question or choose Summarize.",
                        "assistant",
                    )
                    self._set_busy(False)
                elif event == "answer":
                    answer = value
                    self._append_chat("SmartDesk AI", answer, "assistant")
                    question, _ = self.conversation[-1]
                    self.conversation[-1] = (question, answer)
                    self._set_busy(False)
                elif event == "error":
                    self._append_chat("Error", str(value), "error")
                    if self.document_path:
                        self.document_label.configure(
                            text=f"Selected: {self.document_path.name}"
                        )
                    elif self.document_text is None:
                        self.document_label.configure(text="No document selected")
                    self._set_busy(False)
                    messagebox.showerror("SmartDesk AI", str(value))
        except queue.Empty:
            pass
        self.root.after(100, self._process_events)

    def _save_conversation(self) -> None:
        if not self.conversation:
            return
        destination = filedialog.asksaveasfilename(
            title="Save conversation",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="smartdesk-conversation.txt",
        )
        if not destination:
            return

        try:
            with open(destination, "w", encoding="utf-8") as output:
                if self.document_path:
                    output.write(f"Document: {self.document_path}\n\n")
                for question, answer in self.conversation:
                    output.write(f"You: {question}\n")
                    output.write(f"SmartDesk AI: {answer or '(no answer)'}\n\n")
        except OSError as exc:
            messagebox.showerror("Could not save conversation", str(exc))
            return

        self.status_var.set(f"Conversation saved to {destination}")

    def _on_enter(self, _event: tk.Event) -> str:
        self._ask_question()
        return "break"


def main() -> None:
    root = tk.Tk()
    SmartDeskApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
