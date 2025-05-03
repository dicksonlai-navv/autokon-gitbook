import os
import re
import shutil
import unicodedata
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def protect_images(md_text):
    """Wrap image Markdown in tags to prevent AI from altering them."""
    lines = md_text.splitlines()
    protected = []
    for line in lines:
        if line.strip().startswith("![") and "](" in line and ")" in line:
            protected.append(f"<img_protect>{line}</img_protect>")
        else:
            protected.append(line)
    return "\n".join(protected)

def restore_images(translated_text):
    """Remove image protection tags after translation."""
    return translated_text.replace("<img_protect>", "").replace("</img_protect>", "")

def slugify(value):
    """Convert string to a GitBook-compatible slug (e.g. 'How to Login' → 'how-to-login.md')."""
    value = str(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '-', value)

# Translate Markdown files
for root, dirs, files in os.walk("en"):
    for filename in files:
        if filename.endswith(".md"):
            en_path = os.path.join(root, filename)

            with open(en_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            protected_content = protect_images(original_content)

            prompt = (
                "Translate the following Markdown content from English to Bahasa Indonesia. "
                "Do not change formatting. Keep image tags and Markdown syntax untouched.\n\n"
                f"{protected_content}"
            )

            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a helpful translator."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                )

                translated = response.choices[0].message.content
                translated = restore_images(translated)

                # Extract title to create filename
                match = re.search(r"^# (.+)", translated, re.MULTILINE)
                if match:
                    new_slug = slugify(match.group(1)) + ".md"
                else:
                    new_slug = filename  # fallback to original

                # Build output path
                rel_dir = os.path.relpath(os.path.dirname(en_path), "en")
                output_dir = os.path.join("id", rel_dir)
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, new_slug)

                with open(output_path, "w", encoding="utf-8") as out_file:
                    out_file.write(translated)

                print(f"✅ Translated {en_path} → {output_path}")

            except Exception as e:
                print(f"❌ Failed to translate {en_path}: {e}")

# Copy images from en/ to id/
for root, dirs, files in os.walk("en"):
    for filename in files:
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
            en_image_path = os.path.join(root, filename)
            id_image_path = en_image_path.replace("en", "id", 1)

            os.makedirs(os.path.dirname(id_image_path), exist_ok=True)
            shutil.copy2(en_image_path, id_image_path)
            print(f"🖼️ Copied image {en_image_path} → {id_image_path}")
