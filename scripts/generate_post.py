#!/usr/bin/env python3
"""
Generates a blog post draft from a topic using the Gemini API.
Reads config from environment variables, writes a Jekyll post file to _posts/.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import date

API_KEY = os.environ["GEMINI_API_KEY"]
TOPIC = os.environ["TOPIC"]
CATEGORY = os.environ.get("CATEGORY", "Tech")
ANGLE = os.environ.get("ANGLE", "None provided")
SLUG = os.environ["SLUG"]
RUN_NUMBER = os.environ.get("RUN_NUMBER", "0")

MODEL = "gemini-3.6-flash"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

PROMPT = f"""You are a software engineer who writes a personal tech blog read by other \
engineers, DevOps practitioners, and AI builders. Your writing is conversational but \
well-informed: plain language, real opinions, concrete examples, no corporate fluff, \
no "In today's fast-paced world" openers, no bullet-point-soup. Write like a smart \
colleague explaining something over coffee, not like a press release.

Topic: {TOPIC}
Category: {CATEGORY}
Author's angle or notes: {ANGLE}

Write a blog post of 400-600 words on this topic, in Markdown. Structure it with a \
strong opening hook (no generic intro), 2-4 short sections with clear subheadings \
where useful, and a closing thought — not a forced summary paragraph. Do not include \
a title heading inside the body (the title is handled separately). Do not use emojis.

Also write:
- A blog title: specific and interesting, not clickbait, under 70 characters.
- A one or two sentence excerpt suitable as a teaser/meta description.

Return your response as JSON matching the required schema exactly."""

payload = {
    "contents": [{"parts": [{"text": PROMPT}]}],
    "generationConfig": {
        "temperature": 0.85,
        "responseMimeType": "application/json",
        "responseSchema": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING"},
                "excerpt": {"type": "STRING"},
                "body_markdown": {"type": "STRING"},
            },
            "required": ["title", "excerpt", "body_markdown"],
        },
    },
}

req = urllib.request.Request(
    URL,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=90) as resp:
        result = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("Gemini API error:", e.read().decode("utf-8"), file=sys.stderr)
    sys.exit(1)
except urllib.error.URLError as e:
    print("Network error calling Gemini API:", e, file=sys.stderr)
    sys.exit(1)

try:
    text = result["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(text)
    title = parsed["title"].strip().replace("\n", " ")
    excerpt = parsed["excerpt"].strip().replace("\n", " ")
    body = parsed["body_markdown"].strip()
except (KeyError, IndexError, json.JSONDecodeError) as e:
    print("Failed to parse Gemini response:", e, file=sys.stderr)
    print(json.dumps(result, indent=2), file=sys.stderr)
    sys.exit(1)

if not title or not body:
    print("Gemini returned an empty title or body.", file=sys.stderr)
    sys.exit(1)

# Escape double quotes for safe YAML frontmatter
safe_title = title.replace('"', '\\"')
safe_excerpt = excerpt.replace('"', '\\"')

today = date.today().isoformat()
filename = f"_posts/{today}-{SLUG}.md"

frontmatter = (
    "---\n"
    f'title: "{safe_title}"\n'
    f"date: {today}\n"
    f'topic: "{CATEGORY}"\n'
    'status: "passed"\n'
    f"run: {RUN_NUMBER}\n"
    f'excerpt: "{safe_excerpt}"\n'
    "---\n\n"
)

os.makedirs("_posts", exist_ok=True)
with open(filename, "w", encoding="utf-8") as f:
    f.write(frontmatter + body + "\n")

print(f"Wrote {filename}")
print(f"Title: {title}")

gh_output = os.environ.get("GITHUB_OUTPUT")
if gh_output:
    with open(gh_output, "a", encoding="utf-8") as f:
        f.write(f"post_path={filename}\n")
        f.write(f"post_title={title}\n")
