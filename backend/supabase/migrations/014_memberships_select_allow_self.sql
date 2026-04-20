-- Ensure users can always read their own membership rows.
-- This prevents join INSERT ... RETURNING from failing under RLS.

drop policy if exists "memberships_select_attendee_or_creator" on public.event_memberships;

create policy "memberships_select_attendee_or_creator"
on public.event_memberships
for select
to authenticated
using (
  user_id = auth.uid()
  or public.can_view_event_attendees(event_id)
);

