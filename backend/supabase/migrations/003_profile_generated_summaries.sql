-- Add generated profile summary fields for AI-assisted profile cards.

alter table public.profiles
  add column if not exists profile_one_liner text,
  add column if not exists profile_summary text,
  add column if not exists summary_provider text,
  add column if not exists summary_updated_at timestamptz;
