export type FrameDetectionRequest = {
  image_base64: string;
  event_id?: string;
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

  async recognizeFrame(payload: FrameDetectionRequest): Promise<unknown> {
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

    return response.json();
  }

  private async tryParseError(response: Response): Promise<unknown> {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }
}
