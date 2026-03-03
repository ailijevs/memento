-- Recognition results table for real-time streaming from glasses to phone.
-- Glasses capture frames every ~300ms, backend processes and stores matches here.
-- Phone subscribes via Supabase Realtime to display results instantly.

-- ---------- TABLE ----------
create table if not exists public.recognition_results (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  event_id uuid not null references public.events(event_id) on delete cascade,
  matched_user_id uuid references auth.users(id) on delete set null,
  confidence float not null default 0.0,
  created_at timestamptz not null default now()
);

comment on table public.recognition_results is
  'Stores face recognition matches from glasses for real-time phone display';
comment on column public.recognition_results.user_id is
  'The glasses wearer who initiated the recognition';
comment on column public.recognition_results.matched_user_id is
  'The person identified in the frame (null if no match)';
comment on column public.recognition_results.confidence is
  'AWS Rekognition confidence score (0.0 to 1.0)';

-- ---------- INDEXES ----------
-- For querying user's recent results (phone subscription filter)
create index if not exists idx_recognition_results_user_created
  on public.recognition_results(user_id, created_at desc);

-- For cleanup of old results
create index if not exists idx_recognition_results_created
  on public.recognition_results(created_at);

-- For filtering by event
create index if not exists idx_recognition_results_event
  on public.recognition_results(event_id);

-- ---------- RLS ----------
alter table public.recognition_results enable row level security;

-- Users can only SELECT their own recognition results
drop policy if exists "recognition_results_select_own" on public.recognition_results;
create policy "recognition_results_select_own"
on public.recognition_results
for select
using (user_id = auth.uid());

-- Only backend service role can INSERT (not end users)
-- This is enforced by using service_role key for inserts
drop policy if exists "recognition_results_insert_service" on public.recognition_results;
create policy "recognition_results_insert_service"
on public.recognition_results
for insert
with check (false);

-- Users can DELETE their own results (cleanup)
drop policy if exists "recognition_results_delete_own" on public.recognition_results;
create policy "recognition_results_delete_own"
on public.recognition_results
for delete
using (user_id = auth.uid());

-- ---------- REALTIME ----------
-- Enable Realtime for this table so phone can subscribe to INSERT events
-- Note: This requires running in Supabase dashboard or via supabase CLI:
-- ALTER PUBLICATION supabase_realtime ADD TABLE public.recognition_results;

-- Alternatively, if using supabase_realtime publication:
do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime'
    and schemaname = 'public'
    and tablename = 'recognition_results'
  ) then
    alter publication supabase_realtime add table public.recognition_results;
  end if;
exception
  when undefined_object then
    raise notice 'supabase_realtime publication does not exist, skipping realtime setup';
end $$;
