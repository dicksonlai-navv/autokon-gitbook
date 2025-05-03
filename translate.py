#!/usr/bin/env python3
import os, re, argparse, shutil
from pathlib import Path
import openai
from slugify import slugify

def get_slug_from_title(text):
    m = re.search(r'^#\s+(.+)', text, re.MULTILINE)
    return slugify(m.group(1)) + '.md' if m else None

def build_slug_map(src, summary_file, readme_file):
    slug_map = {}
    for md in Path(src).rglob('*.md'):
        rel = md.relative_to(src).as_posix()
        if rel == summary_file or rel == readme_file:
            continue
        content = md.read_text(encoding='utf-8')
        slug = get_slug_from_title(content)
        if not slug:
            raise RuntimeError(f"No H1 found in {md}")
        slug_map[rel] = slug
    # map README.md → README.md
    slug_map[readme_file] = readme_file
    return slug_map

def translate_text(text, src_loc, tgt_loc, model="gpt-4"):
    system = (
        f"You are a translator converting Markdown from {src_loc} → {tgt_loc}. "
        "Preserve image syntax (![alt](url)), frontmatter, code-blocks, HTML tags, and do not rename links."
    )
    resp = openai.chat.completions.create(
        model=model,
        messages=[
            {"role":"system","content": system},
            {"role":"user",  "content": text}
        ]
    )
    return resp.choices[0].message.content

def rewrite_links(md, slug_map):
    # [text](path/to/foo.md) → [text](new-slug.md)
    def repl(m):
        text, link = m.group(1), m.group(2)
        return f"[{text}]({ slug_map.get(link, link) })"
    return re.sub(r'\[([^\]]+)\]\(([^)]+\.md)\)', repl, md)

def process_file(src_path, dst_path, args, slug_map):
    raw = src_path.read_text(encoding='utf-8')
    trans = translate_text(raw, args.source_locale, args.target_locale, args.model)
    fixed = rewrite_links(trans, slug_map)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(fixed, encoding='utf-8')

def process_summary(src_root, dst_root, slug_map, summary_file):
    src = Path(src_root) / summary_file
    out = Path(dst_root) / summary_file
    lines = src.read_text(encoding='utf-8').splitlines()
    new = []
    for ln in lines:
        # replace link targets
        new.append(rewrite_links(ln, slug_map))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(new), encoding='utf-8')

def copy_images(src_root, dst_root):
    for img in Path(src_root).rglob('*'):
        if img.suffix.lower() in {'.png','.jpg','.jpeg','.gif','.svg'}:
            rel = img.relative_to(src_root)
            out = Path(dst_root) / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(img, out)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--source-dir',    default='en')
    p.add_argument('--target-dir',    default='id')
    p.add_argument('--source-locale', default='en')
    p.add_argument('--target-locale', default='id')
    p.add_argument('--summary-file',  default='SUMMARY.md')
    p.add_argument('--readme-file',   default='README.md')
    p.add_argument('--model',         default='gpt-4')
    args = p.parse_args()

    openai.api_key = os.getenv("OPENAI_API_KEY") or ""

    # 1. Build map: original-path → new-slug
    slug_map = build_slug_map(args.source_dir, args.summary_file, args.readme_file)

    # 2. Translate README.md (kept as README.md)
    process_file(
        Path(args.source_dir)/args.readme_file,
        Path(args.target_dir) / args.readme_file,
        args, slug_map
    )

    # 3. Translate all other .md → slugified filenames
    for orig, slug in slug_map.items():
        if orig == args.readme_file:
            continue
        src = Path(args.source_dir) / orig
        dst = Path(args.target_dir) / Path(orig).parent / slug
        process_file(src, dst, args, slug_map)

    # 4. Copy & adjust SUMMARY.md
    process_summary(args.source_dir, args.target_dir, slug_map, args.summary_file)

    # 5. Copy images
    copy_images(args.source_dir, args.target_dir)
