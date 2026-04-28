-- Track which profiles a user has liked.
-- Query pattern optimized for: "get all liked profiles for current user".

create table if not exists public.profile_likes (
  user_id uuid not null references auth.users(id) on delete cascade,
  liked_profile_id uuid not null references public.profiles(user_id) on delete cascade,
  event_id uuid references public.events(event_id) on delete set null,
  created_at timestamptz not null default now(),
  primary key (user_id, liked_profile_id),
  check (user_id <> liked_profile_id)
);

-- Supports user-centric reads scoped to where users met.
create index if not exists idx_profile_likes_user_event
  on public.profile_likes(user_id, event_id);

-- Supports reverse lookups such as "who liked this profile".
create index if not exists idx_profile_likes_liked_profile_id
  on public.profile_likes(liked_profile_id);

alter table public.profile_likes enable row level security;

drop policy if exists "profile_likes_select_own" on public.profile_likes;
create policy "profile_likes_select_own"
on public.profile_likes
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists "profile_likes_insert_own" on public.profile_likes;
create policy "profile_likes_insert_own"
on public.profile_likes
for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists "profile_likes_delete_own" on public.profile_likes;
create policy "profile_likes_delete_own"
on public.profile_likes
for delete
to authenticated
using (auth.uid() = user_id);
