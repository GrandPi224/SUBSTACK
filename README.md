# SUBSTACK

Sources, notes and data behind each article by William "Chip" Corley on [chipcorley.substack.com](https://chipcorley.substack.com).

Published at https://grandpi224.github.io/SUBSTACK/

- `index.html`: everything. Each article is a collapsible block (date on the left, title), and each of its section headings collapses too.
- `sources/<article-slug>/index.html`: a redirect to `index.html#<article-slug>`, which opens that article. Each Substack article links here.
- `assets/site.css`: shared style, light and dark.

To add an article: copy an article block in `index.html` to the top of the list, then copy a redirect page to `sources/<slug>/`. Bump `site.css?v=N` after style changes.
