-- Allow any authenticated user to view active events.
-- This replaces the creator/member-only SELECT policy for events.

drop policy if exists "events_select_creator_or_member" on public.events;
drop policy if exists "events_select_authenticated_active" on public.events;

create policy "events_select_authenticated_active"
on public.events
for select
to authenticated
using (is_active = true);
