# Editing the site

The public site is a small React app, not a folder of plain `.html` files, which is why there is no obvious "website folder." All of it lives in `apps/reviewer-ui/`. For everyday text and styling changes you only need two files.

## Where things are

| You want to change | Open this file |
| --- | --- |
| Page text, headings, links, section copy | `src/App.tsx` |
| Colors, fonts, spacing, layout | `src/styles.css` |
| Browser tab title and social/meta tags | `index.html` |

`src/App.tsx` is JSX. It reads almost like HTML: text sits between tags such as `<h2>...</h2>` and `<p>...</p>`, so to reword a sentence you find that sentence in the file and edit the words between the tags. The top menu is the `<nav className="site-nav">` block; each `<a href="...">Label</a>` is one menu item.

## See your change locally

From the repository root:

```bash
cd apps/reviewer-ui
npm install
npm run dev
```

That opens a local preview (the terminal prints the URL, usually `http://localhost:5173`). Edits to `App.tsx` or `styles.css` refresh the page as you save.

## How it reaches the live site

The live site at `https://imtiazither.github.io/eduwork-databridge/` rebuilds automatically when changes land on the `main` branch, through the GitHub Pages workflow in `.github/workflows/pages.yml`. There is nothing to upload by hand. Commit to `main`, and the site updates within a few minutes.

## A tip on wording

The project keeps copy plain and concrete, and avoids em dashes (use a period or a comma instead). If a sentence starts to read like marketing filler, shorter and more specific is usually better.
