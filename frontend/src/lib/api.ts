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
      "ngrok-skip-browser-warning": "true",
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
      const detail = error.detail;
      const message = Array.isArray(detail)
        ? detail.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join("; ")
        : typeof detail === "string"
        ? detail
        : `Request failed: ${response.status} ${response.statusText}`;
      throw new ApiError(response.status, message);
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

  async updateProfile(data: ProfileUpdateRequest) {
    return this.request<ProfileResponse>("/api/v1/profiles/me", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async getProfileById(userId: string) {
    return this.request<ProfileResponse>(`/api/v1/profiles/${userId}`);
  }

  async getCompatibility(userId: string) {
    return this.request<CompatibilityResponse>(`/api/v1/profiles/${userId}/compatibility`);
  }

  async getEvents() {
    return this.request<EventResponse[]>("/api/v1/events");
  }

  async getMyEvents() {
    return this.request<EventResponse[]>("/api/v1/events/me");
  }

  async getMyOrganizedEvents() {
    return this.request<EventResponse[]>("/api/v1/events/organized");
  }

  async createEvent(data: EventCreateRequest) {
    return this.request<EventResponse>("/api/v1/events", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async deleteEvent(eventId: string) {
    return this.request<void>(`/api/v1/events/${eventId}`, {
      method: "DELETE",
    });
  }

  async updateEvent(eventId: string, data: EventUpdateRequest) {
    return this.request<EventResponse>(`/api/v1/events/${eventId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async joinEvent(eventId: string) {
    return this.request<MembershipResponse>(`/api/v1/events/${eventId}/join`, {
      method: "POST",
    });
  }

  async leaveEvent(eventId: string) {
    return this.request<void>(`/api/v1/events/${eventId}/leave`, {
      method: "DELETE",
    });
  }

  async getMyEventConsent(eventId: string) {
    return this.request<ConsentResponse>(`/api/v1/events/${eventId}/consents/me`);
  }

  async updateMyEventConsent(eventId: string, data: ConsentUpdateRequest) {
    return this.request<ConsentResponse>(`/api/v1/events/${eventId}/consents/me`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async getEventDirectory(eventId: string) {
    return this.request<ProfileDirectoryResponse>(`/api/v1/profiles/directory/${eventId}`);
  }

  async getMyProfileLikes() {
    return this.request<ProfileLikeResponse[]>("/api/v1/profiles/me/likes");
  }

  async likeProfile(userId: string, eventId: string) {
    return this.request<ProfileLikeResponse>(`/api/v1/profiles/${userId}/like`, {
      method: "POST",
      body: JSON.stringify({ event_id: eventId }),
    });
  }

  async unlikeProfile(userId: string) {
    return this.request<void>(`/api/v1/profiles/${userId}/like`, {
      method: "DELETE",
    });
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

  async uploadResume(file: File) {
    if (!this.accessToken) throw new ApiError(401, "Not authenticated");

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_URL}/api/v1/profiles/me/resume`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.accessToken}`,
        "ngrok-skip-browser-warning": "true",
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      const detail = error.detail;
      const message = Array.isArray(detail)
        ? detail.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join("; ")
        : typeof detail === "string"
        ? detail
        : `Resume upload failed: ${response.status} ${response.statusText}`;
      throw new ApiError(response.status, message);
    }

    return response.json() as Promise<ResumeParseResponse>;
  }
}

export const api = new ApiClient();

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export function isApiErrorWithStatus(error: unknown, status: number): error is ApiError {
  return error instanceof ApiError && error.status === status;
}

// ─── Request types ────────────────────────────────────────────────────────────

export interface ProfileUpdateRequest {
  full_name?: string;
  headline?: string;
  bio?: string;
  location?: string;
  company?: string;
  major?: string;
  graduation_year?: number;
  linkedin_url?: string;
  photo_path?: string;
  experiences?: ExperienceInput[];
  education?: EducationInput[];
}

export interface ExperienceInput {
  company?: string | null;
  title?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  description?: string | null;
  location?: string | null;
}

export interface EducationInput {
  school?: string | null;
  degree?: string | null;
  field_of_study?: string | null;
  start_date?: string | null;
  end_date?: string | null;
}

export interface EventCreateRequest {
  name: string;
  starts_at?: string;
  ends_at?: string;
  location?: string;
  is_active?: boolean;
}

export interface EventUpdateRequest {
  name?: string;
  starts_at?: string;
  ends_at?: string;
  location?: string;
  is_active?: boolean;
}

export interface ConsentUpdateRequest {
  allow_profile_display?: boolean;
  allow_recognition?: boolean;
}

// ─── Response types ───────────────────────────────────────────────────────────

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
  // created_at: string;
  // updated_at: string;
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
  completion_score: number;
  missing_fields: string[];
}

export interface LinkedInOnboardingResponse {
  profile: ProfileResponse;
  enrichment: Record<string, unknown>;
  completion: ProfileCompletionResponse;
  image_saved: boolean;
}

export interface ResumeParseResponse {
  message: string;
  extracted_data: Record<string, unknown>;
  profile_updated: boolean;
}

export interface EventResponse {
  event_id: string;
  created_by: string;
  name: string;
  starts_at: string | null;
  ends_at: string | null;
  location: string | null;
  is_active: boolean;
  indexing_status: "pending" | "in_progress" | "completed" | "failed";
  cleanup_status: "pending" | "in_progress" | "completed" | "failed";
  created_at: string;
}

export interface MembershipResponse {
  event_id: string;
  user_id: string;
  role: "owner" | "member";
  joined_at: string;
}

export interface CompatibilityResponse {
  score: number;
  shared_companies: string[];
  shared_schools: string[];
  shared_fields: string[];
  conversation_starters: string[];
}

export interface ProfileDirectoryEntry {
  user_id: string;
  full_name: string;
  headline: string | null;
  company: string | null;
  school: string | null;
  major: string | null;
  photo_path: string | null;
}

export interface ProfileDirectoryResponse {
  entries: ProfileDirectoryEntry[];
  total_count: number;
  hidden_count: number;
}

export interface ProfileLikeResponse {
  user_id: string;
  liked_profile_id: string;
  event_id: string | null;
  event_name: string | null;
  created_at: string;
}

export interface ConsentResponse {
  event_id: string;
  user_id: string;
  allow_profile_display: boolean;
  allow_recognition: boolean;
  consented_at: string | null;
  revoked_at: string | null;
  updated_at: string;
}
