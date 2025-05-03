import os
import re
import shutil
import yaml
from slugify import slugify
from openai import OpenAI

SRC_DIR = "en"
DEST_DIR = "id"
client = OpenAI()

TRANSLATE_SECTIONS = {
    "Getting Started": "Memulai",
    "Real Estate Developers": "Pengembang Real Estat",
    "Contractors": "Kontraktor",
    "Customers": "Pelanggan"
}

TRANSLATION_GUIDE = """
When translating the following Markdown content to Indonesian, follow these consistency rules:
- Do not translate code blocks or image paths.
"""

def translate_text(text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": TRANSLATION_GUIDE},
            {"role": "user", "content": "Translate all the following content into Bahasa Indonesia with consistent terminology and tone. Ensure uniform translation across all elements, including titles, paragraphs, headers, button texts, and hyperlinks. Use the same Indonesian words for repeated English terms to maintain clarity and coherence throughout."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content

def extract_title(content: str) -> str:
    match = re.search(r"^# (.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else "untitled"

def parse_and_translate_front_matter(text: str) -> tuple[str, str]:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            header_raw = text[:end+4]
            body = text[end+4:].lstrip()
            header_clean = header_raw.strip("-\n")
            try:
                metadata = yaml.safe_load(header_clean)
                for key in ["title", "description"]:
                    if key in metadata and isinstance(metadata[key], str):
                        metadata[key] = translate_text(metadata[key])
                rebuilt = "---\n" + yaml.safe_dump(metadata, allow_unicode=True) + "---"
                return rebuilt, body
            except Exception as e:
                return header_raw.strip(), body
    return "", text

def translate_markdown_file(src_path: str, dst_root: str):
    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()

    front_matter, body = parse_and_translate_front_matter(content)
    translated_body = translate_text(body)

    title = extract_title(translated_body)
    translated_slug = slugify(title)
    filename = translated_slug + ".md"

    rel_src_dir = os.path.relpath(os.path.dirname(src_path), SRC_DIR)
    translated_dir = slugify(rel_src_dir) if rel_src_dir != "." else ""
    dst_dir = os.path.join(dst_root, translated_dir)
    os.makedirs(dst_dir, exist_ok=True)

    dst_path = os.path.join(dst_dir, filename)
    with open(dst_path, "w", encoding="utf-8") as f:
        if front_matter:
            f.write(front_matter + "\n\n")
        f.write(translated_body)

    original_slug = os.path.splitext(os.path.basename(src_path))[0]
    copy_icon_asset(original_slug, translated_slug)

    return {
        "src": os.path.relpath(src_path, SRC_DIR),
        "dst": os.path.relpath(dst_path, DEST_DIR),
        "title": title,
        "filename": filename
    }

def copy_icon_asset(original_slug: str, translated_slug: str):
    src_icon = os.path.join(SRC_DIR, ".gitbook/assets", f"{original_slug}.svg")
    dst_icon = os.path.join(DEST_DIR, ".gitbook/assets", f"{translated_slug}.svg")
    if os.path.exists(src_icon):
        os.makedirs(os.path.dirname(dst_icon), exist_ok=True)
        shutil.copy2(src_icon, dst_icon)

def copy_images():
    for root, _, files in os.walk(SRC_DIR):
        for file in files:
            if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                src_file = os.path.join(root, file)
                rel_path = os.path.relpath(src_file, SRC_DIR)
                dst_file = os.path.join(DEST_DIR, rel_path)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copy2(src_file, dst_file)

def copy_gitbook_assets():
    src = os.path.join(SRC_DIR, ".gitbook")
    dst = os.path.join(DEST_DIR, ".gitbook")
    if os.path.exists(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)

def translate_readme(translated_files):
    src_path = os.path.join(SRC_DIR, "README.md")
    dst_path = os.path.join(DEST_DIR, "README.md")
    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()

    translated = translate_text(content)
    path_lookup = {item["src"]: item for item in translated_files}

    def replace_links(text):
        text = re.sub(r"\[(.+?)\]\((.+?)\)", lambda m:
            f"[{path_lookup[m.group(2)]['title']}]({path_lookup[m.group(2)]['dst']})"
            if m.group(2) in path_lookup else m.group(0), text)

        text = re.sub(r"\((https://github.com/.+?/en/(.+?\.md))\)", lambda m:
            f"({m.group(1).replace('/en/', '/id/').replace(m.group(2), path_lookup.get(m.group(2), {}).get('filename', m.group(2)))})",
            text)

        text = re.sub(r"https://github.com/(.+?/en/.+?\.md)", lambda m:
            f"https://github.com/{m.group(1).replace('/en/', '/id/').replace(m.group(1).split('/')[-1], path_lookup.get(m.group(1).split('/')[-1], {}).get('filename', m.group(1).split('/')[-1]))}",
            text)

        text = re.sub(r'<a href=\"([^"]+\.md)\">.*?</a>', lambda m:
            f'<a href="{path_lookup[m.group(1)]["dst"]}">{path_lookup[m.group(1)]["filename"]}</a>'
            if m.group(1) in path_lookup else m.group(0), text)

        return text

    translated = replace_links(translated)

    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(translated)

def generate_summary(translated_files):
    src_path = os.path.join(SRC_DIR, "SUMMARY.md")
    dst_path = os.path.join(DEST_DIR, "SUMMARY.md")

    with open(src_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    path_lookup = {item["src"]: item for item in translated_files}
    updated_lines = []
    link_pattern = re.compile(r"\[(.+?)\]\((.+?)\)")

    for line in lines:
        if link_pattern.search(line):
            line = link_pattern.sub(
                lambda m: f"[{path_lookup[m.group(2)]['title']}]({path_lookup[m.group(2)]['dst']})"
                if m.group(2) in path_lookup else m.group(0), line)
        else:
            for en, id_ in TRANSLATE_SECTIONS.items():
                if en in line.strip():
                    line = line.replace(en, id_)
        updated_lines.append(line)

    with open(dst_path, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)

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
    copy_gitbook_assets()

if __name__ == "__main__":
    main()
