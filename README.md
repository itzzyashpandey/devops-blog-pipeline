# devops-blog-pipeline

A daily tech/DevOps/AI blog that ships itself: a topic goes in, an automated
pipeline drafts the post, generates a thumbnail, publishes it to this site,
posts a teaser to LinkedIn, and archives it into this repo — once a day,
like a release.

**Live site:** _add your GitHub Pages URL here once deployed_

## Status

🚧 Phase 1 complete: repo structure + Jekyll site + Pages deploy workflow.
Content-generation agents land in later phases.

## Structure

```
_layouts/     Page templates (default shell, post template)
_includes/    Shared header/footer partials
_posts/       Published blog posts (Jekyll date-prefixed markdown)
assets/       CSS and generated images
archive/      Per-post folders mirrored here for GitHub contribution history
.github/workflows/   CI: build + deploy to GitHub Pages
```

## Local preview (optional)

```bash
bundle install
bundle exec jekyll serve
```

Then open http://localhost:4000
