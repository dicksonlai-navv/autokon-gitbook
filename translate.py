import os
import re
import shutil
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def protect_images(md_text):
    lines = md_text.splitlines()
    protected = []
    for line in lines:
        if re.match(r"!\[.*\]\(.*\)", line.strip()):
            protected.append(f"<img_protect>{line}</img_protect>")
        else:
            protected.append(line)
    return "\n".join(protected)

def restore_images(md_text):
    return md_text.replace("<img_protect>", "").replace("</img_protect>", "")

def translate_text(text):
    protected_text = protect_images(text)
    prompt = (
        "Translate the following Markdown content from English to Bahasa Indonesia. "
        "Keep the formatting and Markdown syntax, and do not alter image links.\n\n"
        f"{protected_text}"
    )
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful translator."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return restore_images(response.choices[0].message.content)

def parse_summary(summary_path):
    with open(summary_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    slug_map = {}
    for line in lines:
        match = re.match(r'\s*\*\s*\[(.*?)\]\((.*?)\)', line)
        if match:
            _, path = match.groups()
            slug = os.path.splitext(os.path.basename(path))[0]
            slug_map[path] = slug
    return slug_map, lines

def write_translated_summary(lines_en, slug_map_en_to_id, dest_path):
    with open(dest_path, "w", encoding="utf-8") as f:
        for line in lines_en:
            match = re.match(r'(\s*\*\s*\[.*?\]\()(.*?)(\))', line)
            if match:
                pre, old_path, post = match.groups()
                new_slug = slug_map_en_to_id.get(old_path, old_path)
                f.write(f"{pre}{new_slug}{post}\n")
            else:
                f.write(line)

def translate_markdown_files(slug_map_en_to_id):
    for en_rel_path, id_slug in slug_map_en_to_id.items():
        en_path = os.path.join("en", en_rel_path)
        if not en_path.endswith(".md") or not os.path.isfile(en_path):
            continue

        with open(en_path, "r", encoding="utf-8") as f:
            content = f.read()

        translated = translate_text(content)

        id_path = os.path.join("id", os.path.dirname(en_rel_path), f"{id_slug}.md")
        os.makedirs(os.path.dirname(id_path), exist_ok=True)
        with open(id_path, "w", encoding="utf-8") as f:
            f.write(translated)

def copy_images():
    for root, _, files in os.walk("en"):
        for file in files:
            if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                src = os.path.join(root, file)
                dest = src.replace("en", "id", 1)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(src, dest)

# Main execution
if __name__ == "__main__":
    # Step 1: Translate SUMMARY.md
    with open("en/SUMMARY.md", "r", encoding="utf-8") as f:
        summary_en = f.read()

    summary_translated = translate_text(summary_en)
    os.makedirs("id", exist_ok=True)
    with open("id/SUMMARY.md", "w", encoding="utf-8") as f:
        f.write(summary_translated)

    # Step 2: Parse slugs
    slug_map_en, lines_en = parse_summary("en/SUMMARY.md")
    slug_map_id, _ = parse_summary("id/SUMMARY.md")
    slug_map_en_to_id = {k: v for k, v in zip(slug_map_en.keys(), slug_map_id.values())}

    # Step 3–4: Translate .md files with translated slugs
    translate_markdown_files(slug_map_en_to_id)

    # Step 5–6: Copy image assets
    copy_images()

    # Optional: Overwrite id/SUMMARY.md with consistent slugs
    write_translated_summary(lines_en, slug_map_en_to_id, "id/SUMMARY.md")

    print("✅ Translation complete. Files written to /id/")
