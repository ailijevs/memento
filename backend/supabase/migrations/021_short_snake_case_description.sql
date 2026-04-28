-- Allow auth.users deletion to succeed even if recognition_logs rows reference
-- the user. We keep historical log rows for analytics/audit but null out the
-- user reference instead of blocking the delete.

ALTER TABLE public.recognition_logs
    ALTER COLUMN recognized_user_id DROP NOT NULL;

ALTER TABLE public.recognition_logs
    DROP CONSTRAINT recognition_logs_recognized_user_id_fkey;

ALTER TABLE public.recognition_logs
    ADD CONSTRAINT recognition_logs_recognized_user_id_fkey
    FOREIGN KEY (recognized_user_id)
    REFERENCES auth.users(id)
    ON DELETE SET NULL;