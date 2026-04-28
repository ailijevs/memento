-- Allow auth.users deletion when the user is referenced as the observer in
-- recognition_attempts. Mirrors the SET NULL pattern used for
-- recognition_logs so account deletion is no longer blocked by this FK.
-- Historical attempt rows are preserved with a NULL observer reference.

ALTER TABLE public.recognition_attempts
    ALTER COLUMN observer_user_id DROP NOT NULL;

ALTER TABLE public.recognition_attempts
    DROP CONSTRAINT recognition_attempts_observer_user_id_fkey;

ALTER TABLE public.recognition_attempts
    ADD CONSTRAINT recognition_attempts_observer_user_id_fkey
    FOREIGN KEY (observer_user_id)
    REFERENCES auth.users(id)
    ON DELETE SET NULL;