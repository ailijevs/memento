-- Remove deprecated membership check-in timestamp column.

alter table if exists public.event_memberships
  drop column if exists checked_in_at;
