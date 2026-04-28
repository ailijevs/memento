-- Self-service account deletion.
--
-- Allows an authenticated user to delete their own account using *only* their
-- own JWT. The function runs with SECURITY DEFINER so deleting the auth.users
-- row no longer requires the service-role key in application code.
--
-- Cleanup chain:
--   1. public.events created by the caller are deleted first because
--      public.events.created_by has ON DELETE RESTRICT.
--   2. The auth.users row is deleted, which cascades to:
--        - public.profiles            (ON DELETE CASCADE)
--        - public.event_memberships   (ON DELETE CASCADE)
--        - public.event_consents      (ON DELETE CASCADE)
--        - auth.sessions / auth.refresh_tokens / auth.identities
--          (cascade in the auth schema's own FK definitions)
--
-- AWS-side cleanup (S3 profile photo, Rekognition collections / face entries)
-- is performed by the API layer before this function is called, since those
-- live outside Postgres.

CREATE OR REPLACE FUNCTION public.delete_my_account()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth, pg_temp
AS $$
DECLARE
    uid uuid := auth.uid();
BEGIN
    IF uid IS NULL THEN
        RAISE EXCEPTION 'not authenticated' USING errcode = '28000';
    END IF;

    DELETE FROM public.events WHERE created_by = uid;
    DELETE FROM auth.users    WHERE id         = uid;
END;
$$;

REVOKE ALL    ON FUNCTION public.delete_my_account() FROM public;
GRANT EXECUTE ON FUNCTION public.delete_my_account() TO authenticated;
