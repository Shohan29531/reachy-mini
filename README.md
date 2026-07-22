# Reachy Mini Chatbot

A small proof-of-concept chatbot for Reachy Mini.  
You type a question in the terminal, Ollama Cloud generates the response, macOS converts it to speech, and Reachy Mini reads it aloud.

## Requirements

- macOS
- Reachy Mini connected by USB
- Reachy Mini Control app open and connected
- Conda
- Ollama API key

## Setup

```bash
conda create -n reachy-mini-chat python=3.12 -y
conda activate reachy-mini-chat

pip install -U ollama reachy-mini
```

Set your Ollama API key:

```bash
export OLLAMA_API_KEY="your-ollama-api-key"
```

## Run

From the project folder:

```bash
conda activate reachy-mini-chat
python reachy_chatbot.py
```

Then type your question:

```text
You: good morning
```

Type `exit`, `quit`, or `q` to stop.

## Notes

- This uses Ollama Cloud for chatbot responses.
- This uses macOS `say` for text-to-speech.
- Keep Reachy Mini Control open while running the chatbot.
- Do not run another Reachy app at the same time.
