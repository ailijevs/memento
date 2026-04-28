-- Store per-user notification preferences.

create table if not exists public.user_notification_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email_notifications boolean not null default true,
  event_updates boolean not null default true,
  host_messages boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Backfill preferences for users that already exist.
insert into public.user_notification_preferences (user_id)
select id
from auth.users
on conflict (user_id) do nothing;

alter table public.user_notification_preferences enable row level security;

drop policy if exists "notification_prefs_select_own" on public.user_notification_preferences;
create policy "notification_prefs_select_own"
on public.user_notification_preferences
for select
to authenticated
using (user_id = auth.uid());

drop policy if exists "notification_prefs_insert_own" on public.user_notification_preferences;
create policy "notification_prefs_insert_own"
on public.user_notification_preferences
for insert
to authenticated
with check (user_id = auth.uid());

drop policy if exists "notification_prefs_update_own" on public.user_notification_preferences;
create policy "notification_prefs_update_own"
on public.user_notification_preferences
for update
to authenticated
using (user_id = auth.uid())
with check (user_id = auth.uid());

do $$ begin
  create trigger trg_user_notification_preferences_updated_at
  before update on public.user_notification_preferences
  for each row execute function public.set_updated_at();
exception when duplicate_object then null; end $$;
