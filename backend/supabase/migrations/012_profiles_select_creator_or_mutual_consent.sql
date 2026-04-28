-- Profiles visibility:
-- 1) Users can always see their own profile.
-- 2) Event creators can see profiles of attendees in events they created.
-- 3) Attendees can see each other only when both sides allow_profile_display=true
--    for at least one shared event.

drop policy if exists "profiles_select_same_event" on public.profiles;
drop policy if exists "profiles_select_creator_or_mutual_consent" on public.profiles;

create policy "profiles_select_creator_or_mutual_consent"
on public.profiles
for select
to authenticated
using (
  auth.uid() = user_id
  or exists (
    select 1
    from public.event_memberships m_target
    join public.events e
      on e.event_id = m_target.event_id
    where m_target.user_id = profiles.user_id
      and e.created_by = auth.uid()
  )
  or exists (
    select 1
    from public.event_memberships m_me
    join public.event_memberships m_them
      on m_them.event_id = m_me.event_id
    join public.event_consents c_me
      on c_me.event_id = m_me.event_id
     and c_me.user_id = m_me.user_id
    join public.event_consents c_them
      on c_them.event_id = m_them.event_id
     and c_them.user_id = m_them.user_id
    where m_me.user_id = auth.uid()
      and m_them.user_id = profiles.user_id
      and c_me.allow_profile_display = true
      and c_them.allow_profile_display = true
  )
);

