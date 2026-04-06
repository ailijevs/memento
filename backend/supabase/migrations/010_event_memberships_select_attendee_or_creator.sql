-- Allow reading attendee lists when caller is either:
-- 1) RSVP'd to the same event, or
-- 2) the event creator.
--
-- We use a SECURITY DEFINER helper to avoid recursive RLS checks on
-- public.event_memberships when evaluating membership-based visibility.

create or replace function public.can_view_event_attendees(p_event_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select
    exists (
      select 1
      from public.event_memberships me
      where me.event_id = p_event_id
        and me.user_id = auth.uid()
    )
    or exists (
      select 1
      from public.events e
      where e.event_id = p_event_id
        and e.created_by = auth.uid()
    );
$$;

revoke all on function public.can_view_event_attendees(uuid) from public;
grant execute on function public.can_view_event_attendees(uuid) to authenticated;

drop policy if exists "memberships_select_same_event" on public.event_memberships;
drop policy if exists "memberships_select_attendee_or_creator" on public.event_memberships;

create policy "memberships_select_attendee_or_creator"
on public.event_memberships
for select
to authenticated
using (public.can_view_event_attendees(event_id));

