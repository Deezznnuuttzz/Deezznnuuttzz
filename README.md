# Caterin

General UI shell for Caterin Software — navigation, layout, and theme foundation for catering operations (events, menus, orders, clients).

## Stack

- Static HTML / CSS / vanilla JS (no build step)
- Google Fonts: Cormorant Garamond (brand/display) + Outfit (UI)
- Fits the existing GitHub Pages workflow (`.github/workflows/static.yml`)

## Run locally

From the repo root:

```bash
python3 -m http.server 4173
```

Open [http://127.0.0.1:4173](http://127.0.0.1:4173).

Any static file server works (`npx serve`, VS Code Live Server, etc.).

## What’s in the shell

- Sidebar + mobile nav: Home, Events, Menus, Orders, Clients
- Home: brand-forward first viewport (not a stats dashboard)
- Placeholder list views for the four ops areas
- Shared theme tokens in `css/shell.css`
