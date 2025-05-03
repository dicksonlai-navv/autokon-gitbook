import os
import re
import openai
import shutil
from slugify import slugify

SRC_DIR = "en"
DEST_DIR = "id"
openai.api_key = os.getenv("OPENAI_API_KEY")

def translate_text(text: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Translate the following Markdown content to Indonesian. Do not translate code blocks or image links."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content

def extract_title(content: str) -> str:
    match = re.search(r"^# (.+)$", content, re.MULTILINE)
    return match.group(1) if match else "untitled"

def translate_markdown_file(src_path: str, dst_root: str):
    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()
    translated = translate_text(content)
    title = extract_title(translated)
    filename = slugify(title) + ".md"
    rel_dir = os.path.relpath(os.path.dirname(src_path), SRC_DIR)
    os.makedirs(os.path.join(dst_root, rel_dir), exist_ok=True)
    dst_path = os.path.join(dst_root, rel_dir, filename)
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(translated)
    return title, filename, os.path.relpath(dst_path, start=DEST_DIR)

def copy_images():
    for root, _, files in os.walk(SRC_DIR):
        for file in files:
            if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                src_file = os.path.join(root, file)
                rel_path = os.path.relpath(src_file, SRC_DIR)
                dst_file = os.path.join(DEST_DIR, rel_path)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copy2(src_file, dst_file)

def translate_readme():
    src_path = os.path.join(SRC_DIR, "README.md")
    dst_path = os.path.join(DEST_DIR, "README.md")
    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()
    translated = translate_text(content)
    # Placeholder: update links here after full file list translation
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(translated)

def generate_summary(translated_map):
    src_path = os.path.join(SRC_DIR, "SUMMARY.md")
    dst_path = os.path.join(DEST_DIR, "SUMMARY.md")
    with open(src_path, "r", encoding="utf-8") as f:
        summary = f.read()
    def replace_link(match):
        link_text = match.group(1)
        link_url = match.group(2)
        new_entry = translated_map.get(link_url)
        return f"[{link_text}]({new_entry})" if new_entry else match.group(0)
    updated = re.sub(r"\[(.+?)\]\((.+?)\)", replace_link, summary)
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(updated)

def main():
    translated_map = {}
    for root, _, files in os.walk(SRC_DIR):
        for file in files:
            if file.endswith(".md") and file not in ["README.md", "SUMMARY.md"]:
                src_file = os.path.join(root, file)
                title, filename, rel_dst = translate_markdown_file(src_file, DEST_DIR)
                rel_src = os.path.relpath(src_file, start=SRC_DIR)
                translated_map[rel_src] = rel_dst
    translate_readme()
    generate_summary(translated_map)
    copy_images()

if __name__ == "__main__":
    main()
