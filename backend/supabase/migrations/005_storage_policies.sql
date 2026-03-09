-- Allow authenticated users to upload/update their own profile photo
-- File must be named {user_id}.jpg at the root of the profile-photos bucket

insert into storage.buckets (id, name, public)
values ('profile-photos', 'profile-photos', true)
on conflict (id) do update set public = true;

create policy "Users can upload their own photo"
  on storage.objects for insert
  to authenticated
  with check (
    bucket_id = 'profile-photos'
    and name = (auth.uid()::text || '.jpg')
  );

create policy "Users can update their own photo"
  on storage.objects for update
  to authenticated
  using (
    bucket_id = 'profile-photos'
    and name = (auth.uid()::text || '.jpg')
  );

create policy "Anyone can read profile photos"
  on storage.objects for select
  to public
  using (bucket_id = 'profile-photos');
