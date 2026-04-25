import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const originalFetch = globalThis.fetch;

let ApiClient: new () => { setToken: (t: string) => void; getProfile: () => Promise<unknown> };
let ApiError: new (status: number, message: string) => Error & { status: number };
let isApiErrorWithStatus: (error: unknown, status: number) => boolean;
let apiInstance: InstanceType<typeof ApiClient>;

describe("ApiClient", () => {
  const mockFetch = vi.fn();

  beforeEach(async () => {
    vi.resetModules();
    globalThis.fetch = mockFetch;
    mockFetch.mockClear();

    const mod = await import("../api");
    ApiError = mod.ApiError;
    isApiErrorWithStatus = mod.isApiErrorWithStatus;
    apiInstance = mod.api;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("includes Authorization header when token is set", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ user_id: "u1" }),
    });

    apiInstance.setToken("my-token");
    await apiInstance.getProfile();

    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers.Authorization).toBe("Bearer my-token");
  });

  it("includes Content-Type and ngrok headers", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    apiInstance.setToken("token");
    await apiInstance.getProfile();

    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.headers["ngrok-skip-browser-warning"]).toBe("true");
  });

  it("throws ApiError with string detail on non-ok response", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: () => Promise.resolve({ detail: "Profile not found" }),
    });

    apiInstance.setToken("token");
    await expect(apiInstance.getProfile()).rejects.toThrow("Profile not found");
  });

  it("throws ApiError with joined array detail", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 422,
      statusText: "Unprocessable Entity",
      json: () =>
        Promise.resolve({
          detail: [
            { msg: "field required", loc: ["body", "name"] },
            { msg: "invalid email", loc: ["body", "email"] },
          ],
        }),
    });

    apiInstance.setToken("token");
    await expect(apiInstance.getProfile()).rejects.toThrow(
      "field required; invalid email"
    );
  });

  it("throws ApiError with fallback message when detail is not string/array", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve({ detail: { nested: true } }),
    });

    apiInstance.setToken("token");
    await expect(apiInstance.getProfile()).rejects.toThrow(
      "Request failed: 500 Internal Server Error"
    );
  });

  it("throws ApiError with fallback when response body is not JSON", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      json: () => Promise.reject(new Error("not json")),
    });

    apiInstance.setToken("token");
    await expect(apiInstance.getProfile()).rejects.toThrow(
      "Request failed: 502 Bad Gateway"
    );
  });

  it("returns undefined for 204 responses", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 204,
      json: () => Promise.reject(new Error("no body")),
    });

    apiInstance.setToken("token");
    const result = await (apiInstance as unknown as { getProfile: () => Promise<unknown> }).getProfile();
    expect(result).toBeUndefined();
  });

  it("constructs URL from API_URL env + path", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    apiInstance.setToken("token");
    await apiInstance.getProfile();

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/v1/profiles/me");
  });
});

describe("ApiError", () => {
  it("has status and message properties", async () => {
    const mod = await import("../api");
    const error = new mod.ApiError(403, "Forbidden");
    expect(error.status).toBe(403);
    expect(error.message).toBe("Forbidden");
    expect(error.name).toBe("ApiError");
    expect(error).toBeInstanceOf(Error);
  });
});

describe("isApiErrorWithStatus", () => {
  it("returns true for matching ApiError", async () => {
    const mod = await import("../api");
    const error = new mod.ApiError(404, "Not found");
    expect(mod.isApiErrorWithStatus(error, 404)).toBe(true);
  });

  it("returns false for wrong status", async () => {
    const mod = await import("../api");
    const error = new mod.ApiError(404, "Not found");
    expect(mod.isApiErrorWithStatus(error, 500)).toBe(false);
  });

  it("returns false for non-ApiError", async () => {
    const mod = await import("../api");
    const error = new Error("Regular error");
    expect(mod.isApiErrorWithStatus(error, 500)).toBe(false);
  });

  it("returns false for null/undefined", async () => {
    const mod = await import("../api");
    expect(mod.isApiErrorWithStatus(null, 500)).toBe(false);
    expect(mod.isApiErrorWithStatus(undefined, 500)).toBe(false);
  });
});
