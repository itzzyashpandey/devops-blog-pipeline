#!/usr/bin/env python3
"""
Generates a thumbnail image for a post using the Gemini image API, falling
back to Pollinations.ai if that fails. Also injects the resulting image
path into the post's frontmatter so the Jekyll layout picks it up.
"""

import base64
import glob
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import date

API_KEY = os.environ["GEMINI_API_KEY"]
TOPIC = os.environ["TOPIC"]
CATEGORY = os.environ.get("CATEGORY", "Tech")
POST_TITLE = os.environ.get("POST_TITLE", TOPIC)
SLUG = os.environ["SLUG"]

IMAGE_MODEL = "gemini-3.1-flash-image"
IMAGE_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{IMAGE_MODEL}:generateContent?key={API_KEY}"
)

# Matches the blog's actual CSS design tokens, so generated thumbnails feel
# like part of one consistent site rather than random stock-art per post.
STYLE = (
    "Minimalist abstract editorial illustration for a tech blog. "
    "Dark ink-navy background, hex E8A33D as the primary accent color, "
    "5FAE8B as a secondary accent used sparingly. Clean geometric shapes, "
    "subtle grid or circuit-like linework, conceptual and abstract rather "
    "than literal or photographic. No text, no words, no letters, no logos "
    "anywhere in the image. No photographic human faces. Wide 16:9 "
    "hero-image composition, professional and modern, suitable as a blog "
    "header image."
)

PROMPT = (
    f"{STYLE} The concept this image should evoke: \"{POST_TITLE}\" — a "
    f"topic in the {CATEGORY} space. Specifically about: {TOPIC}."
)

today = date.today().isoformat()
image_filename = f"{today}-{SLUG}.png"
image_path = f"assets/images/{image_filename}"


def try_gemini():
    payload = {
        "contents": [{"parts": [{"text": PROMPT}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": "16:9", "imageSize": "1K"},
        },
    }
    req = urllib.request.Request(
        IMAGE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            return base64.b64decode(inline["data"])
    raise ValueError(f"No image data in Gemini response: {json.dumps(result)[:500]}")


def try_pollinations():
    encoded_prompt = urllib.parse.quote(PROMPT)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width=1200&height=675&nologo=true"
    )
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read()


image_bytes = None
source = None

try:
    image_bytes = try_gemini()
    source = "gemini"
except Exception as e:
    print(f"Gemini image generation failed, falling back to Pollinations: {e}", file=sys.stderr)
    try:
        image_bytes = try_pollinations()
        source = "pollinations"
    except Exception as e2:
        print(f"Pollinations fallback also failed: {e2}", file=sys.stderr)
        sys.exit(1)

os.makedirs("assets/images", exist_ok=True)
with open(image_path, "wb") as f:
    f.write(image_bytes)

print(f"Wrote {image_path} (source: {source})")

# Inject the image path into the matching post's frontmatter
matches = glob.glob(f"_posts/{today}-{SLUG}.md")
if not matches:
    print("Could not find matching post file to update frontmatter.", file=sys.stderr)
    sys.exit(1)

post_file = matches[0]
with open(post_file, "r", encoding="utf-8") as f:
    content = f.read()

parts = content.split("---", 2)
if len(parts) < 3:
    print("Post file does not have expected frontmatter structure.", file=sys.stderr)
    sys.exit(1)

frontmatter_body = parts[1]
rest = parts[2]
frontmatter_body += f'image: "/{image_path}"\n'
new_content = "---" + frontmatter_body + "---" + rest

with open(post_file, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Updated frontmatter in {post_file}")

gh_output = os.environ.get("GITHUB_OUTPUT")
if gh_output:
    with open(gh_output, "a", encoding="utf-8") as f:
        f.write(f"image_path={image_path}\n")
        f.write(f"image_source={source}\n")
