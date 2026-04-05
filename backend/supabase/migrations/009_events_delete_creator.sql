-- Allow organizers to hard-delete only their own events.

DROP POLICY IF EXISTS "events_delete_creator" ON public.events;

CREATE POLICY "events_delete_creator"
ON public.events
FOR DELETE
TO authenticated
USING (created_by = auth.uid());
