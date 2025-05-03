import os
import re
import shutil
from slugify import slugify
from openai import OpenAI

SRC_DIR = "en"
DEST_DIR = "id"
client = OpenAI()

def translate_text(text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Translate the following Markdown content to Indonesian. Do not translate code blocks or image links."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content

def extract_title(content: str) -> str:
    match = re.search(r"^# (.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else "untitled"

def translate_markdown_file(src_path: str, dst_root: str):
    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()
    translated = translate_text(content)
    title = extract_title(translated)
    filename = slugify(title) + ".md"

    rel_src_dir = os.path.relpath(os.path.dirname(src_path), SRC_DIR)
    translated_dir = slugify(rel_src_dir) if rel_src_dir != "." else ""
    dst_dir = os.path.join(dst_root, translated_dir)
    os.makedirs(dst_dir, exist_ok=True)

    dst_path = os.path.join(dst_dir, filename)
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(translated)

    return {
        "src": os.path.relpath(src_path, SRC_DIR),
        "dst": os.path.relpath(dst_path, DEST_DIR),
        "title": title
    }

def copy_images():
    for root, _, files in os.walk(SRC_DIR):
        for file in files:
            if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                src_file = os.path.join(root, file)
                rel_path = os.path.relpath(src_file, SRC_DIR)
                dst_file = os.path.join(DEST_DIR, rel_path)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copy2(src_file, dst_file)

def translate_readme(translated_files):
    src_path = os.path.join(SRC_DIR, "README.md")
    dst_path = os.path.join(DEST_DIR, "README.md")
    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()

    translated = translate_text(content)

    path_lookup = {item["src"]: item for item in translated_files}

    def replace_link(match):
        link_text = match.group(1)
        link_url = match.group(2)
        if link_url in path_lookup:
            new = path_lookup[link_url]
            return f"[{new['title']}]({new['dst']})"
        return match.group(0)

    updated = re.sub(r"\[(.+?)\]\((.+?)\)", replace_link, translated)

    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(updated)

def generate_summary(translated_files):
    src_path = os.path.join(SRC_DIR, "SUMMARY.md")
    dst_path = os.path.join(DEST_DIR, "SUMMARY.md")

    with open(src_path, "r", encoding="utf-8") as f:
        summary = f.read()

    path_lookup = {item["src"]: item for item in translated_files}

    def replace_link(match):
        link_text = match.group(1)
        link_url = match.group(2)
        if link_url in path_lookup:
            new = path_lookup[link_url]
            return f"[{new['title']}]({new['dst']})"
        return match.group(0)

    updated = re.sub(r"\[(.+?)\]\((.+?)\)", replace_link, summary)

    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(updated)

def main():
    translated_files = []
    for root, _, files in os.walk(SRC_DIR):
        for file in files:
            if file.endswith(".md") and file not in ["README.md", "SUMMARY.md"]:
                src_file = os.path.join(root, file)
                translated_files.append(translate_markdown_file(src_file, DEST_DIR))

    translate_readme(translated_files)
    generate_summary(translated_files)
    copy_images()

if __name__ == "__main__":
    main()
