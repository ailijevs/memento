-- Add event processing status columns for indexing and cleanup workflows.

do $$ begin
  create type event_processing_status as enum ('pending', 'in_progress', 'completed', 'failed');
exception when duplicate_object then null; end $$;

alter table if exists public.events
  add column if not exists indexing_status event_processing_status not null default 'pending',
  add column if not exists cleanup_status event_processing_status not null default 'pending';

