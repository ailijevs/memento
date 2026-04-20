import {
  api,
  type ProfilePhotoUploadSource,
  type ProfileResponse,
} from "@/lib/api";

export async function uploadProfilePhoto(
  file: File,
  source: ProfilePhotoUploadSource = "onboarding"
): Promise<ProfileResponse> {
  const requestedContentType = file.type.trim() || "image/jpeg";
  const uploadMeta = await api.requestProfilePhotoUploadUrl({
    content_type: requestedContentType,
    source,
  });

  let uploadResponse: Response;
  try {
    uploadResponse = await fetch(uploadMeta.upload_url, {
      method: "PUT",
      headers: {
        "Content-Type": uploadMeta.content_type,
      },
      body: file,
    });
  } catch {
    throw new Error("S3 upload request failed. Please try again.");
  }
  if (!uploadResponse.ok) {
    throw new Error(`S3 upload failed with status ${uploadResponse.status}.`);
  }

  return api.confirmProfilePhotoUpload({ s3_key: uploadMeta.s3_key });
}
