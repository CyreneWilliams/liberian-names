-- Run once in Supabase: SQL Editor > New query > paste > Run.
-- Records whether a contributor agreed to how their recording is used,
-- and stops recordings without consent from being saved.
alter table public.contributions add column if not exists consent boolean not null default false;

alter table public.contributions drop constraint if exists recordings_need_consent;
alter table public.contributions add constraint recordings_need_consent
  check (consent or (clip = '' and clip_slow = '')) not valid;  -- "not valid": older recordings are kept as they are
