export type FrameDetectionRequest = {
  image_base64: string;
  event_id?: string;
};

export type ProfileCard = {
  user_id: string;
  full_name: string;
  headline: string | null;
  company: string | null;
  photo_path: string | null;
  profile_one_liner: string | null;
  face_similarity: number;
  experience_similarity: number | null;
  bio: string | null;
  location: string | null;
  major: string | null;
  graduation_year: number | null;
  linkedin_url: string | null;
  profile_summary: string | null;
  experiences: Record<string, unknown>[] | null;
  education: Record<string, unknown>[] | null;
};

export type FrameDetectionResponse = {
  matches: ProfileCard[];
  processing_time_ms: number;
  event_id: string | null;
};

type ErrorPayload = {
  detail?: string;
  message?: string;
};

export class BackendClient {
  private readonly recognitionUrl: string;

  constructor(recognitionUrl?: string) {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    this.recognitionUrl = recognitionUrl || `${backendUrl}/recognition/detect`;
  }

  async recognizeFrame(payload: FrameDetectionRequest): Promise<FrameDetectionResponse> {
    const response = await fetch(this.recognitionUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorPayload = (await this.tryParseError(response)) as ErrorPayload | null;
      const errorText = errorPayload?.detail || errorPayload?.message || response.statusText;
      throw new Error(`Recognition request failed (${response.status}): ${errorText}`);
    }

    return response.json() as Promise<FrameDetectionResponse>;
  }

  private async tryParseError(response: Response): Promise<unknown> {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }
}
