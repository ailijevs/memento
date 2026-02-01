-- =========================
-- MEMENTO MVP (Same-event-only)
-- Supabase Postgres SQL
-- Tables: profiles, events, event_memberships, event_consents
-- RLS: profiles visible only if same event + target consent
-- =========================

create extension if not exists "pgcrypto";

-- ---------- ENUMS ----------
do $$ begin
  create type membership_role as enum ('attendee', 'organizer', 'admin');
exception when duplicate_object then null; end $$;

-- ---------- TABLES ----------
-- Global user profile (1 row per user)
create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null,
  headline text,
  bio text,
  company text,
  major text,
  graduation_year int,
  linkedin_url text,
  photo_path text, -- Supabase Storage path (not raw bytes)
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Event metadata
create table if not exists public.events (
  event_id uuid primary key default gen_random_uuid(),
  name text not null,
  starts_at timestamptz,
  ends_at timestamptz,
  location text,
  is_active boolean not null default true,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now()
);

-- Event membership = the hard scope gate
create table if not exists public.event_memberships (
  event_id uuid not null references public.events(event_id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role membership_role not null default 'attendee',
  checked_in_at timestamptz,
  created_at timestamptz not null default now(),
  primary key (event_id, user_id)
);

-- Consent is per-event (recommended)
-- Default is FALSE (explicit opt-in)
create table if not exists public.event_consents (
  event_id uuid not null references public.events(event_id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  allow_profile_display boolean not null default false,
  allow_recognition boolean not null default false,
  consented_at timestamptz,
  revoked_at timestamptz,
  updated_at timestamptz not null default now(),
  primary key (event_id, user_id)
);

create index if not exists idx_event_memberships_user on public.event_memberships(user_id);
create index if not exists idx_event_memberships_event on public.event_memberships(event_id);
create index if not exists idx_event_consents_event on public.event_consents(event_id);

-- ---------- updated_at trigger ----------
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

do $$ begin
  create trigger trg_profiles_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();
exception when duplicate_object then null; end $$;

do $$ begin
  create trigger trg_event_consents_updated_at
  before update on public.event_consents
  for each row execute function public.set_updated_at();
exception when duplicate_object then null; end $$;

-- ---------- Directory Function ----------
-- Returns profiles for an event directory (only consented users)
create or replace function public.get_event_directory(p_event_id uuid)
returns table (
  user_id uuid,
  full_name text,
  headline text,
  company text,
  photo_path text
)
language sql
security invoker
as $$
  select
    p.user_id,
    p.full_name,
    p.headline,
    p.company,
    p.photo_path
  from public.event_memberships m
  join public.event_consents c
    on c.event_id = m.event_id
   and c.user_id  = m.user_id
  join public.profiles p
    on p.user_id = m.user_id
  where m.event_id = p_event_id
    and c.allow_profile_display = true;
$$;

-- =========================
-- RLS
-- =========================
alter table public.profiles enable row level security;
alter table public.events enable row level security;
alter table public.event_memberships enable row level security;
alter table public.event_consents enable row level security;

-- ---- PROFILES ----
-- Select: you can see your own profile OR another user's profile only if:
-- (a) you share an event membership AND (b) that user has allow_profile_display=true for that event
drop policy if exists "profiles_select_same_event" on public.profiles;
create policy "profiles_select_same_event"
on public.profiles
for select
using (
  auth.uid() = user_id
  OR exists (
    select 1
    from public.event_memberships m_me
    join public.event_memberships m_them
      on m_them.event_id = m_me.event_id
    join public.event_consents c
      on c.event_id = m_them.event_id
     and c.user_id  = m_them.user_id
    where m_me.user_id = auth.uid()
      and m_them.user_id = profiles.user_id
      and c.allow_profile_display = true
  )
);

-- Insert/Update: only your own profile
drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own"
on public.profiles
for insert
with check (auth.uid() = user_id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own"
on public.profiles
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

-- ---- EVENTS ----
-- Select: only members of the event OR creator
drop policy if exists "events_select_creator_or_member" on public.events;
create policy "events_select_creator_or_member"
on public.events
for select
using (
  created_by = auth.uid()
  OR exists (
    select 1 from public.event_memberships m
    where m.event_id = events.event_id
      and m.user_id = auth.uid()
  )
);

-- Insert: creator is the inserter
drop policy if exists "events_insert_creator" on public.events;
create policy "events_insert_creator"
on public.events
for insert
with check (created_by = auth.uid());

-- Update: only creator (MVP)
drop policy if exists "events_update_creator" on public.events;
create policy "events_update_creator"
on public.events
for update
using (created_by = auth.uid())
with check (created_by = auth.uid());

-- ---- EVENT MEMBERSHIPS ----
-- Select: you can see memberships for events you are in
drop policy if exists "memberships_select_same_event" on public.event_memberships;
create policy "memberships_select_same_event"
on public.event_memberships
for select
using (
  exists (
    select 1 from public.event_memberships m
    where m.event_id = event_memberships.event_id
      and m.user_id = auth.uid()
  )
);

-- Insert: you can only insert your own membership (join event)
drop policy if exists "memberships_insert_self" on public.event_memberships;
create policy "memberships_insert_self"
on public.event_memberships
for insert
with check (user_id = auth.uid());

-- Update/Delete: only yourself (MVP)
drop policy if exists "memberships_update_self" on public.event_memberships;
create policy "memberships_update_self"
on public.event_memberships
for update
using (user_id = auth.uid())
with check (user_id = auth.uid());

drop policy if exists "memberships_delete_self" on public.event_memberships;
create policy "memberships_delete_self"
on public.event_memberships
for delete
using (user_id = auth.uid());

-- ---- EVENT CONSENTS ----
-- Select: you can read your own consent rows
drop policy if exists "consents_select_own" on public.event_consents;
create policy "consents_select_own"
on public.event_consents
for select
using (user_id = auth.uid());

-- Insert/Update: only your own consent for events you are a member of
drop policy if exists "consents_insert_own_if_member" on public.event_consents;
create policy "consents_insert_own_if_member"
on public.event_consents
for insert
with check (
  user_id = auth.uid()
  and exists (
    select 1 from public.event_memberships m
    where m.event_id = event_consents.event_id
      and m.user_id = auth.uid()
  )
);

drop policy if exists "consents_update_own_if_member" on public.event_consents;
create policy "consents_update_own_if_member"
on public.event_consents
for update
using (
  user_id = auth.uid()
  and exists (
    select 1 from public.event_memberships m
    where m.event_id = event_consents.event_id
      and m.user_id = auth.uid()
  )
)
with check (
  user_id = auth.uid()
  and exists (
    select 1 from public.event_memberships m
    where m.event_id = event_consents.event_id
      and m.user_id = auth.uid()
  )
);

-- Delete consent (when leaving event)
drop policy if exists "consents_delete_own" on public.event_consents;
create policy "consents_delete_own"
on public.event_consents
for delete
using (user_id = auth.uid());
