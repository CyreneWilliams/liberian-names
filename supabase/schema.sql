-- Liberian Names: database setup
-- Paste this whole file into Supabase > SQL Editor and click Run.
-- It is safe to run again: it only adds what is missing and refreshes the rules.
--
-- What it creates
--   contributions   what visitors send. Anyone can add one; only editors can read or review them.
--   approved        contributions an editor approved. Everyone can read these; the site shows them.
--   editors         the email addresses allowed to review. Starts with mail@cyrenewilliams.com.
--   pending-audio   private storage for recordings waiting for review.
--   audio           public storage for approved recordings.
-- The 424 names themselves live in the site's code (data/names.json), so no names table is needed.

-- ---------- tables ----------
create table if not exists public.editors (
  email text primary key
);

create table if not exists public.contributions (
  id          uuid primary key default gen_random_uuid(),
  kind        text not null check (kind in ('new', 'spelling', 'meaning', 'audio')),
  name        text not null check (char_length(btrim(name)) between 1 and 80),
  target      text not null default '' check (char_length(target) <= 80),
  variants    text[] not null default '{}' check (cardinality(variants) <= 20),
  tribe       text not null default '' check (char_length(tribe) <= 40),
  gender      text not null default '' check (gender in ('', 'F', 'M', 'U')),
  meaning     text not null default '' check (char_length(meaning) <= 300),
  pron        text not null default '' check (char_length(pron) <= 80),
  story       text not null default '' check (char_length(story) <= 2000),
  credit      text not null default '' check (char_length(credit) <= 80),
  source      text not null default 'other' check (source in ('family', 'speaker', 'elder', 'other')),
  clip        text not null default '' check (char_length(clip) <= 120),
  clip_slow   text not null default '' check (char_length(clip_slow) <= 120),
  status      text not null default 'pending' check (status in ('pending', 'approved', 'declined')),
  created_at  timestamptz not null default now(),
  reviewed_at timestamptz
);
create index if not exists contributions_status_created on public.contributions (status, created_at);

create table if not exists public.approved (
  id          uuid primary key,
  kind        text not null,
  name        text not null,
  target      text not null default '',
  variants    text[] not null default '{}',
  tribe       text not null default '',
  gender      text not null default '',
  meaning     text not null default '',
  pron        text not null default '',
  story       text not null default '',
  credit      text not null default '',
  clip        text not null default '',
  clip_slow   text not null default '',
  approved_at timestamptz not null default now()
);

insert into public.editors (email) values ('mail@cyrenewilliams.com') on conflict do nothing;

-- ---------- helper functions ----------
-- True when the signed-in person's email is on the editor list.
create or replace function public.is_editor()
returns boolean
language sql stable security definer
set search_path = public
as $$
  select exists (
    select 1 from public.editors e
    where lower(e.email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );
$$;

-- Lets a visitor see the status of contributions they sent (by their private ids), and nothing else.
create or replace function public.contribution_status(ids uuid[])
returns table (id uuid, status text)
language sql stable security definer
set search_path = public
as $$
  select c.id, c.status from public.contributions c
  where c.id = any (ids[1:200]);
$$;

revoke all on function public.is_editor() from public;
revoke all on function public.contribution_status(uuid[]) from public;
grant execute on function public.is_editor() to anon, authenticated;
grant execute on function public.contribution_status(uuid[]) to anon, authenticated;

-- ---------- access rules ----------
alter table public.editors enable row level security;
alter table public.contributions enable row level security;
alter table public.approved enable row level security;

revoke all on public.editors from anon, authenticated;
grant insert on public.contributions to anon, authenticated;
grant select, update, delete on public.contributions to authenticated;
grant select on public.approved to anon, authenticated;
grant insert, update, delete on public.approved to authenticated;

drop policy if exists "Anyone can send a contribution" on public.contributions;
create policy "Anyone can send a contribution" on public.contributions
  for insert to anon, authenticated
  with check (status = 'pending' and reviewed_at is null);

drop policy if exists "Editors read contributions" on public.contributions;
create policy "Editors read contributions" on public.contributions
  for select to authenticated using (public.is_editor());

drop policy if exists "Editors review contributions" on public.contributions;
create policy "Editors review contributions" on public.contributions
  for update to authenticated using (public.is_editor()) with check (public.is_editor());

drop policy if exists "Editors delete contributions" on public.contributions;
create policy "Editors delete contributions" on public.contributions
  for delete to authenticated using (public.is_editor());

drop policy if exists "Everyone reads approved" on public.approved;
create policy "Everyone reads approved" on public.approved
  for select to anon, authenticated using (true);

drop policy if exists "Editors add approved" on public.approved;
create policy "Editors add approved" on public.approved
  for insert to authenticated with check (public.is_editor());

drop policy if exists "Editors change approved" on public.approved;
create policy "Editors change approved" on public.approved
  for update to authenticated using (public.is_editor()) with check (public.is_editor());

drop policy if exists "Editors remove approved" on public.approved;
create policy "Editors remove approved" on public.approved
  for delete to authenticated using (public.is_editor());

-- ---------- recordings ----------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('pending-audio', 'pending-audio', false, 2097152, array['audio/*', 'video/mp4', 'video/3gpp']),
  ('audio',         'audio',         true,  2097152, array['audio/*', 'video/mp4', 'video/3gpp'])
on conflict (id) do update
  set public = excluded.public,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "Anyone can upload a recording for review" on storage.objects;
create policy "Anyone can upload a recording for review" on storage.objects
  for insert to anon, authenticated
  with check (bucket_id = 'pending-audio');

drop policy if exists "Editors listen to recordings for review" on storage.objects;
create policy "Editors listen to recordings for review" on storage.objects
  for select to authenticated
  using (bucket_id = 'pending-audio' and public.is_editor());

drop policy if exists "Editors remove recordings for review" on storage.objects;
create policy "Editors remove recordings for review" on storage.objects
  for delete to authenticated
  using (bucket_id = 'pending-audio' and public.is_editor());

drop policy if exists "Editors manage published recordings" on storage.objects;
create policy "Editors manage published recordings" on storage.objects
  for all to authenticated
  using (bucket_id = 'audio' and public.is_editor())
  with check (bucket_id = 'audio' and public.is_editor());
