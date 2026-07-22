from pathlib import Path
import os
import json
import tempfile
import time
import wave
import subprocess
import urllib.request

from ollama import Client
from reachy_mini import ReachyMini


OLLAMA_MODEL = "gpt-oss:20b"

SYSTEM_PROMPT = """
You are Reachy Mini, a friendly tabletop robot.
Answer in English only.
Keep responses concise, natural, and easy to speak aloud.
If web search results are provided, answer using them.
If the answer is not in the search results, say you could not verify it.
Avoid markdown unless the user asks for code.
"""


LIVE_INFO_KEYWORDS = {
    "today", "tomorrow", "now", "current", "currently", "latest",
    "weather", "temperature", "forecast",
    "match", "matches", "game", "games", "score", "schedule",
    "news", "price", "stock", "rate", "open", "closed",
    "near me", "this week", "this weekend"
}


def get_api_key() -> str:
    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OLLAMA_API_KEY is missing. Run: export OLLAMA_API_KEY='your-key-here'"
        )
    return api_key


def make_ollama_client() -> Client:
    api_key = get_api_key()
    return Client(
        host="https://ollama.com",
        headers={"Authorization": "Bearer " + api_key},
    )


ollama_client = make_ollama_client()


def needs_web_search(user_text: str) -> bool:
    text = user_text.lower()
    return any(keyword in text for keyword in LIVE_INFO_KEYWORDS)


def ollama_web_search(query: str, max_results: int = 5) -> list[dict]:
    api_key = get_api_key()

    payload = json.dumps({"query": query}).encode("utf-8")

    req = urllib.request.Request(
        "https://ollama.com/api/web_search",
        data=payload,
        method="POST",
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data.get("results", [])[:max_results]


def format_search_results(results: list[dict]) -> str:
    if not results:
        return "No web search results found."

    blocks = []
    for i, r in enumerate(results, start=1):
        title = r.get("title", "").strip()
        url = r.get("url", "").strip()
        content = r.get("content", "").strip()

        blocks.append(
            f"Result {i}\nTitle: {title}\nURL: {url}\nSnippet: {content}"
        )

    return "\n\n".join(blocks)


def ask_ollama(user_text: str, history: list[tuple[str, str]]) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT.strip()}]

    for user_msg, bot_msg in history[-4:]:
        if user_msg.strip() and bot_msg.strip():
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": bot_msg})

    if needs_web_search(user_text):
        search_results = ollama_web_search(user_text)
        search_context = format_search_results(search_results)

        final_user_prompt = f"""
User question:
{user_text}

Web search results:
{search_context}

Answer the user using the web search results. Be concise and natural for spoken output.
"""
    else:
        final_user_prompt = user_text

    messages.append({"role": "user", "content": final_user_prompt.strip()})

    response = ollama_client.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        stream=False,
        think="low",
        options={
            "temperature": 0.4,
            "num_predict": 500,
        },
    )

    try:
        content = response.message.content
    except Exception:
        content = response.get("message", {}).get("content", "")

    content = (content or "").strip()

    if not content:
        return "Sorry, I got an empty response from the model."

    return content


def text_to_wav_with_macos_say(text: str, wav_path: Path) -> None:
    text_file = wav_path.with_suffix(".txt")
    text_file.write_text(text, encoding="utf-8")

    subprocess.run(
        [
            "say",
            "-v",
            "Samantha",
            "-r",
            "180",
            "--file-format=WAVE",
            "--data-format=LEI16@22050",
            "-o",
            str(wav_path),
            "-f",
            str(text_file),
        ],
        check=True,
    )


def wav_duration_seconds(wav_path: Path) -> float:
    with wave.open(str(wav_path), "rb") as wav_file:
        return wav_file.getnframes() / float(wav_file.getframerate())


def main():
    print("Connecting to Reachy Mini...")
    print("Keep Reachy Mini Control open and connected over USB.")
    print("Using Ollama Cloud for chat.")
    print("Using Ollama Web Search for live/current questions.")
    print("Using macOS say for speech generation.")
    print("Type 'exit' to stop.\n")

    history: list[tuple[str, str]] = []

    with ReachyMini(connection_mode="localhost_only", media_backend="default") as mini:
        print("Connected. Chatbot ready.\n")

        while True:
            user_text = input("You: ").strip()

            if user_text.lower() in {"exit", "quit", "q"}:
                print("Goodbye.")
                break

            if not user_text:
                continue

            try:
                answer = ask_ollama(user_text, history)
                print(f"Reachy: {answer}\n")

                if answer.strip() and "empty response" not in answer.lower():
                    history.append((user_text, answer))

                with tempfile.TemporaryDirectory() as tmpdir:
                    wav_path = Path(tmpdir) / "reachy_response.wav"
                    text_to_wav_with_macos_say(answer, wav_path)

                    mini.media.play_sound(str(wav_path))
                    time.sleep(wav_duration_seconds(wav_path) + 0.5)

            except KeyboardInterrupt:
                print("\nGoodbye.")
                break

            except Exception as e:
                print(f"\nError: {e}")
                print("Check OLLAMA_API_KEY, Ollama Cloud, Reachy Mini Control, and USB.\n")


if __name__ == "__main__":
    main()