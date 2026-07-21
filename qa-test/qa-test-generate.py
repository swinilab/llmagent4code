import os
import re
from datetime import datetime
from dotenv import load_dotenv
from ollama import Client

load_dotenv()

# Config
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "your-api-key-here")
MODEL = "glm-5.2:cloud"          # qwen3-coder:480b was retired — swap if needed
OUTPUT_DIR = "outputs"
PROMPT_FILE = "augmented_prompt.md"

client = Client(
    host="https://ollama.com",
    headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"}
)

def load_prompt(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Prompt file not found: {path}. Put it in the current working "
            f"directory or update PROMPT_FILE."
        )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def chat(prompt: str) -> str:
    response = client.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"]

def extract_block(text: str, start: str, end: str) -> str:
    """Pull the text between two delimiter lines. Returns '' if not found."""
    pattern = re.escape(start) + r"(.*?)" + re.escape(end)
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else ""

def split_and_save(answer: str, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)

    reasoning = extract_block(answer, "===REASONING_START===", "===REASONING_END===")
    csv_text  = extract_block(answer, "===CSV_START===", "===CSV_END===")

    # Strip stray markdown code fences from the CSV block, just in case
    csv_text = re.sub(r"^```[a-zA-Z]*\n?", "", csv_text)
    csv_text = re.sub(r"\n?```$", "", csv_text).strip()

    paths = {}

    if csv_text:
        csv_path = os.path.join(out_dir, "tactics.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            f.write(csv_text + "\n")
        paths["tactics.csv"] = csv_path
    else:
        print("WARNING: no CSV block found in the response.")

    if reasoning:
        md_path = os.path.join(out_dir, "reasoning.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(reasoning + "\n")
        paths["reasoning.md"] = md_path
    else:
        print("WARNING: no reasoning block found in the response.")

    # Fallback: if neither delimiter was found, dump the raw response so nothing is lost
    if not paths:
        raw_path = os.path.join(out_dir, f"raw_{datetime.now():%Y%m%d_%H%M%S}.md")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(answer)
        paths["raw"] = raw_path
        print("Delimiters missing — saved raw response instead. "
              "The model didn't follow the output format.")

    return paths

if __name__ == "__main__":
    prompt = load_prompt(PROMPT_FILE)
    answer = chat(prompt)
    saved = split_and_save(answer, OUTPUT_DIR)

    for name, path in saved.items():
        print(f"Wrote {name}: {path}")