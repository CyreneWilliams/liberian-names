# Liberian Names

An open, community-built archive of Liberian traditional names: meanings, tribes, spellings, recordings and the people who shared them.

A project by Cyrene Williams and Winifred Gray-Johnson, co-founders and contributors.

## What's in this repository

| Path | What it is |
|---|---|
| `index.html` | The website. Built from the two files below; don't edit it by hand. |
| `src/template.html` | The page design and code, with a `__DATA__` placeholder for the names. |
| `data/names.json` | The 424 given names and 17 family names (cleaned October 2026). |
| `scripts/build_site.py` | Rebuilds `index.html` after `data/names.json` or the template changes. |
| `supabase/schema.sql` | One-paste database setup: contributions, approvals, editors, recordings and their access rules. |
| `assets/vendor/` | A pinned copy of the Supabase browser library (v2.117.3, MIT licence). |
| `_headers` | Security headers for Cloudflare Pages. |

## How it works

- The names ship with the page, so search, filters and name pages work even when the database can't be reached.
- Anyone can send a new name, spelling, meaning or recording. Each one goes into Supabase as **pending**. Nobody but an editor can read pending contributions.
- An editor signs in with a one-time email link (footer: **Editor sign-in**) and approves or declines each one. Approved contributions appear on the site straight away.
- Recordings wait in the private `pending-audio` storage. Approving copies them to the public `audio` storage.
- Editors are the emails in the `editors` table. It starts with `mail@cyrenewilliams.com`. To add Winifred, run this in Supabase SQL Editor:
  `insert into public.editors (email) values ('her email address');`

## Setting it up

1. **Database:** in Supabase open **SQL Editor**, paste all of `supabase/schema.sql` and click **Run**.
2. **Sign-in links:** in Supabase open **Authentication > URL Configuration**. Set **Site URL** to the site's address, for example `https://liberiannames.com`. Under **Redirect URLs**, add the test address too, for example `https://liberian-names.pages.dev`.
3. **Hosting:** in Cloudflare open **Workers & Pages > Create > Pages > Connect to Git** and pick this repository. Set the framework preset to **None**, leave the build command empty and set the output directory to `/`. Then click **Save and Deploy**.

## Updating the names

Edit `data/names.json`, then run:

```
python3 scripts/build_site.py
```

and commit the new `index.html`.

## Keys

`src/template.html` contains the Supabase **Project URL** and **publishable** key. Both are designed to be public: the rules in `supabase/schema.sql` decide what they can do. Never commit a `secret` or `service_role` key, or the database password.
