# Out There Together website

Public static marketing website for `outtheretogether.com`.

This repository intentionally contains only website files that are safe to publish. The mobile app, Supabase backend, PhotoDNA scanner, product documentation, credentials and test data are private Blockbeam intellectual property and belong in `outthere-product`, never here.

Read [AGENTS.md](AGENTS.md) before making changes.

## Contents

- `index.html` and `assets/` — marketing homepage and public brand assets.
- `privacy/`, `cookies/`, `delete-account/`, `verification-complete/` — public support and policy pages.
- `cruise-lines/` — one page per cruise line with its member total, plus the list. Built by `scripts/build_cruise_lines.py`, which `.github/workflows/cruise-line-totals.yml` runs once a day. Do not edit these pages by hand: change the script and run it.
- `CNAME` — custom domain configuration.

## Deployment

Publish from the `main` branch using GitHub Pages with the custom domain `outtheretogether.com`. Verify the homepage and a policy page after each deployment.
