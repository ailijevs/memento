-- Add description and max_participants columns to events.

alter table if exists public.events
  add column if not exists description text,
  add column if not exists max_participants integer;
