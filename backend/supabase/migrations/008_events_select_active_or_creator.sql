-- Allow authenticated users to view active events, while allowing organizers
-- to still read their own events after archiving (is_active = false).

alter policy "events_select_authenticated_active"
on "public"."events"
to authenticated
using (
  (is_active = true) OR (created_by = auth.uid())
);

