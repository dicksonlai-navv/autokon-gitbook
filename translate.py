# translate.py
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
os.makedirs('id', exist_ok=True)

for filename in os.listdir('en'):
    if filename.endswith('.md'):
        with open(f'en/{filename}', 'r', encoding='utf-8') as f:
            content = f.read()

        prompt = f"Translate the following Markdown content from English to Bahasa Indonesia. Keep formatting unchanged:\n\n{content}"

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful translator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        translated = response.choices[0].message.content
        with open(f'id/{filename}', 'w', encoding='utf-8') as out_file:
            out_file.write(translated)
