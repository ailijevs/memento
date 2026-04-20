-- Ensure event directory ordering is:
-- 1) current RSVP'd user first
-- 2) remaining attendees alphabetically by name (case-insensitive)

create or replace function public.get_event_directory(p_event_id uuid)
returns table (
  user_id uuid,
  full_name text,
  headline text,
  company text,
  photo_path text,
  major text,
  education jsonb
)
language sql
security invoker
as $$
  select
    p.user_id,
    p.full_name,
    p.headline,
    p.company,
    p.photo_path,
    p.major,
    p.education
  from public.event_memberships m
  join public.profiles p
    on p.user_id = m.user_id
  where m.event_id = p_event_id
  order by
    (m.user_id = auth.uid()) desc,
    lower(p.full_name) asc;
$$;

