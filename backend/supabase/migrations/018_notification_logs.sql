-- Log notification delivery attempts.

do $$ begin
  create type notification_type as enum ('event_update', 'host_message');
exception when duplicate_object then null; end $$;

do $$ begin
  create type notification_status as enum ('sent', 'failed');
exception when duplicate_object then null; end $$;

create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  event_id uuid references public.events(event_id) on delete set null,
  type notification_type not null,
  status notification_status not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_notifications_user_created_at
  on public.notifications(user_id, created_at desc);

create index if not exists idx_notifications_event
  on public.notifications(event_id);

alter table public.notifications enable row level security;

-- No RLS policies on purpose: clients cannot read/write this table.

create or replace function public.prevent_notifications_mutation()
returns trigger
language plpgsql
as $$
begin
  raise exception 'notifications rows are immutable';
end;
$$;

drop trigger if exists trg_notifications_prevent_update on public.notifications;
create trigger trg_notifications_prevent_update
before update on public.notifications
for each row execute function public.prevent_notifications_mutation();

drop trigger if exists trg_notifications_prevent_delete on public.notifications;
create trigger trg_notifications_prevent_delete
before delete on public.notifications
for each row execute function public.prevent_notifications_mutation();
