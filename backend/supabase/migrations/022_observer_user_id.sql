-- Allow auth.users deletion when the user is referenced as the observer in
-- recognition_logs. Mirrors the earlier change for recognized_user_id: keep
-- the historical row, just null out the user reference.

ALTER TABLE public.recognition_logs
    ALTER COLUMN observer_user_id DROP NOT NULL;

ALTER TABLE public.recognition_logs
    DROP CONSTRAINT recognition_logs_observer_user_id_fkey;

ALTER TABLE public.recognition_logs
    ADD CONSTRAINT recognition_logs_observer_user_id_fkey
    FOREIGN KEY (observer_user_id)
    REFERENCES auth.users(id)
    ON DELETE SET NULL;