const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private accessToken: string | null = null;

  setToken(token: string) {
    this.accessToken = token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (this.accessToken) {
      headers["Authorization"] = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        error.detail || `Request failed: ${response.statusText}`
      );
    }

    if (response.status === 204) return undefined as T;
    return response.json();
  }

  async getProfile() {
    return this.request<ProfileResponse>("/api/v1/profiles/me");
  }

  async getProfileCompletion() {
    return this.request<ProfileCompletionResponse>(
      "/api/v1/profiles/me/completion"
    );
  }

  async onboardFromLinkedIn(linkedinUrl: string) {
    return this.request<LinkedInOnboardingResponse>(
      "/api/v1/profiles/onboard-from-linkedin-url",
      {
        method: "POST",
        body: JSON.stringify({ linkedin_url: linkedinUrl }),
      }
    );
  }
}

export const api = new ApiClient();

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

// Response types matching the backend schemas
export interface ProfileResponse {
  user_id: string;
  full_name: string;
  headline: string | null;
  bio: string | null;
  location: string | null;
  company: string | null;
  major: string | null;
  graduation_year: number | null;
  linkedin_url: string | null;
  photo_path: string | null;
  experiences: Experience[] | null;
  education: Education[] | null;
  profile_one_liner: string | null;
  profile_summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface Experience {
  company: string | null;
  title: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
  location: string | null;
}

export interface Education {
  school: string | null;
  degree: string | null;
  field_of_study: string | null;
  start_date: string | null;
  end_date: string | null;
}

export interface ProfileCompletionResponse {
  is_complete: boolean;
  completion_percentage: number;
  filled_fields: string[];
  missing_fields: string[];
}

export interface LinkedInOnboardingResponse {
  profile: ProfileResponse;
  enrichment: Record<string, unknown>;
  completion: ProfileCompletionResponse;
  image_saved: boolean;
}
