import os
import re
import shutil
import unicodedata
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def protect_images(md_text):
    lines = md_text.splitlines()
    protected = []
    for line in lines:
        if line.strip().startswith("![") and "](" in line and ")" in line:
            protected.append(f"<img_protect>{line}</img_protect>")
        else:
            protected.append(line)
    return "\n".join(protected)

def restore_images(translated_text):
    return translated_text.replace("<img_protect>", "").replace("</img_protect>", "")

def translate_summary():
    with open("en/SUMMARY.md", "r", encoding="utf-8") as f:
        lines = f.readlines()

    translated_lines = []
    for line in lines:
        match = re.match(r"(\s*)- \[(.+?)\]\((.+?)\)", line)
        if match:
            indent, title, link = match.groups()
            prompt = f"Translate this page title into Bahasa Indonesia (keep it short): {title}"
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful translator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            translated_title = response.choices[0].message.content.strip().strip('"')
            translated_lines.append(f"{indent}- [{translated_title}]({link})\n")
        else:
            translated_lines.append(line)

    os.makedirs("id", exist_ok=True)
    with open("id/SUMMARY.md", "w", encoding="utf-8") as f:
        f.writelines(translated_lines)

def extract_slug_map():
    slug_map = {}
    with open("id/SUMMARY.md", "r", encoding="utf-8") as f:
        for line in f:
            match = re.match(r"\s*-\s*\[.+?\]\((.+?)\)", line)
            if match:
                path = match.group(1)
                full_path = os.path.normpath(path)
                slug_map[os.path.normpath(os.path.join("id", full_path))] = True
    return slug_map

def slug_matches(path, slug_map):
    for slug in slug_map:
        if os.path.dirname(path) == os.path.dirname(slug):
            return slug
    return None

def slugify(text):
    value = str(text)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '-', value)

def translate_markdown_files(slug_map):
    for root, dirs, files in os.walk("en"):
        for filename in files:
            if filename.endswith(".md"):
                en_path = os.path.join(root, filename)

                with open(en_path, "r", encoding="utf-8") as f:
                    content = f.read()

                protected = protect_images(content)

                prompt = (
                    "Translate the following Markdown content from English to Bahasa Indonesia. "
                    "Keep formatting and image links exactly the same:\n\n" + protected
                )

                try:
                    response = client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are a helpful translator."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2
                    )
                    translated = response.choices[0].message.content
                    translated = restore_images(translated)

                    # Match correct output path from slug_map
                    rel_dir = os.path.relpath(root, "en")
                    match = re.search(r"# (.+)", translated)
                    if match:
                        title = match.group(1)
                        guessed_name = slugify(title) + ".md"
                        guess_path = os.path.join("id", rel_dir, guessed_name)
                        final_path = slug_matches(guess_path, slug_map) or guess_path
                    else:
                        final_path = os.path.join("id", rel_dir, filename)

                    os.makedirs(os
