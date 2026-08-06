# Out There Together public website repository

This is the public, static marketing website only. It exists so `outtheretogether.com` can be deployed without exposing any product source code.

## Strict scope

Allowed here:

- public HTML, CSS, JavaScript and image assets for the marketing site;
- public privacy, cookie, account-deletion and verification-complete pages;
- the `CNAME` and static-hosting configuration needed to publish those pages.

Never add any of the following:

- Expo or React Native app source, `app/`, mobile builds or app dependencies;
- Supabase migrations, Edge Functions, database schema, service configuration or deployment tooling;
- the PhotoDNA scanner, server configuration or any backend service;
- credentials, keys, tokens, private preview URLs, supplier feeds, test data, user data or internal operational documents.

The private `outthere-product` repository owns all product code, backend code and implementation documentation. The private `blockbeam-vault` owns business context, brand, legal facts and durable decisions. If a proposed website change needs either kind of material, keep that material out of this repository.

## Publishing rules

- Treat every tracked file as publicly readable.
- Keep the website marketing-only. It must not expose development-client access, internal inventory, unapproved partner data or authenticated product routes.
- Preserve the `CNAME` unless the approved public-domain strategy changes.
- Before publishing, check that every local asset reference resolves and inspect the homepage plus one policy page at the live domain.
