#!/usr/bin/env python3
"""
Generates a thumbnail image for a post using Pollinations.ai (free, no API
key required). Injects the resulting image path into the post's frontmatter
if successful. If image generation fails after retries, the pipeline
continues WITHOUT an image rather than failing the whole run — the Jekyll
layout already handles a missing page.image gracefully.
"""

import glob
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import date

TOPIC = os.environ["TOPIC"]
CATEGORY = os.environ.get("CATEGORY", "Tech")
POST_TITLE = os.environ.get("POST_TITLE", TOPIC)
SLUG = os.environ["SLUG"]

# The referrer Pollinations uses to identify legitimate traffic — set to
# your site's own domain. Safe to hardcode since it's public information.
REFERRER = os.environ.get("SITE_REFERRER", "itzzyashpandey.github.io")

# Matches the blog's actual CSS design tokens, so generated thumbnails feel
# like part of one consistent site rather than random stock-art per post.
STYLE = (
    "Minimalist abstract editorial illustration for a tech blog. "
    "Dark ink-navy background, warm amber as the primary accent color, "
    "muted sage-green as a secondary accent used sparingly. Clean geometric "
    "shapes, subtle grid or circuit-like linework, conceptual and abstract "
    "rather than literal or photographic. No text, no words, no letters, no "
    "logos anywhere in the image. No photographic human faces. Professional "
    "and modern, suitable as a blog header image."
)

PROMPT = (
    f"{STYLE} The concept this image should evoke: \"{POST_TITLE}\" — a "
    f"topic in the {CATEGORY} space. Specifically about: {TOPIC}."
)

today = date.today().isoformat()
image_filename = f"{today}-{SLUG}.png"
image_path = f"assets/images/{image_filename}"


def try_pollinations(attempt_timeout=60):
    encoded_prompt = urllib.parse.quote(PROMPT)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width=1200&height=675&nologo=true&referrer={REFERRER}"
    )
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
        },
    )
    with urllib.request.urlopen(req, timeout=attempt_timeout) as resp:
        return resp.read()


image_bytes = None
source = None
last_error = None

for attempt in range(1, 4):
    try:
        image_bytes = try_pollinations()
        source = "pollinations"
        break
    except Exception as e:
        last_error = e
        print(f"Attempt {attempt}/3 failed: {e}", file=sys.stderr)
        if attempt < 3:
            time.sleep(5 * attempt)

if image_bytes is None:
    print(
        f"Image generation failed after 3 attempts, continuing without a "
        f"thumbnail for this post. Last error: {last_error}",
        file=sys.stderr,
    )
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write("image_source=none\n")
    sys.exit(0)

os.makedirs("assets/images", exist_ok=True)
with open(image_path, "wb") as f:
    f.write(image_bytes)

print(f"Wrote {image_path} (source: {source})")

matches = glob.glob(f"_posts/{today}-{SLUG}.md")
if not matches:
    print("Could not find matching post file to update frontmatter.", file=sys.stderr)
    sys.exit(0)

post_file = matches[0]
with open(post_file, "r", encoding="utf-8") as f:
    content = f.read()

parts = content.split("---", 2)
if len(parts) < 3:
    print("Post file does not have expected frontmatter structure.", file=sys.stderr)
    sys.exit(0)

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
