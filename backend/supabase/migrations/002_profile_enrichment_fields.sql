-- Add profile fields needed for automated LinkedIn onboarding and completion checks.

alter table public.profiles
  add column if not exists location text,
  add column if not exists experiences jsonb not null default '[]'::jsonb,
  add column if not exists education jsonb not null default '[]'::jsonb;
