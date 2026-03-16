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

export type SocketMessage =
  | { type: "start_recognition"; payload?: { event_id?: string } }
  | { type: "stop_recognition"; payload?: undefined }
  | { type: "connected"; payload: { clientId: string } }
  | { type: "ack"; payload: { receivedType: string } }
  | { type: "error"; payload: { reason: string } }
  | { type: "recognition_status"; payload: { status: string } }
  | { type: "recognition_error"; payload: { message: string } }
  | {
      type: "recognition_result";
      payload: { timestamp: string; result: FrameDetectionResponse };
    };

type MessageHandler = (message: SocketMessage) => void | Promise<void>;

/**
 * Browser WebSocket client for the glasses-app websocket server.
 * Supports message fan-out to registered handlers.
 */
const RECONNECT_DELAYS_MS = [2000, 4000, 8000, 15000, 30000];

export class SocketClient {
  private readonly url: string;
  private socket: WebSocket | null = null;
  private readonly messageHandlers = new Set<MessageHandler>();
  private shouldReconnect = false;
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(url?: string) {
    this.url = url || process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8080";
  }

  connect(): void {
    this.shouldReconnect = true;
    this.reconnectAttempt = 0;
    this._connect();
  }

  private _connect(): void {
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN ||
        this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    this.socket = new WebSocket(this.url);

    this.socket.onopen = () => {
      console.log(`[SocketClient] Connected to ${this.url}`);
      this.reconnectAttempt = 0;
    };

    this.socket.onmessage = (event) => {
      const message = this.parseMessage(event.data);
      if (!message) {
        console.error("[SocketClient] Received invalid message payload:", event.data);
        return;
      }

      for (const handler of this.messageHandlers) {
        Promise.resolve(handler(message)).catch((error) => {
          console.error("[SocketClient] Message handler failed:", error);
        });
      }
    };

    this.socket.onerror = () => {
      // Browser WebSocket error events intentionally contain no detail.
      // The most common cause is the glasses-app server not running at this.url.
      console.warn(`[SocketClient] Could not connect to ${this.url} — is the glasses-app running?`);
    };

    this.socket.onclose = (event) => {
      if (event.wasClean) {
        console.log(`[SocketClient] Disconnected cleanly (code ${event.code})`);
      } else {
        console.warn(`[SocketClient] Connection lost (code ${event.code})`);
      }
      this.socket = null;
      if (this.shouldReconnect) {
        this._scheduleReconnect();
      }
    };
  }

  private _scheduleReconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    const delay = RECONNECT_DELAYS_MS[Math.min(this.reconnectAttempt, RECONNECT_DELAYS_MS.length - 1)];
    this.reconnectAttempt++;
    console.log(`[SocketClient] Reconnecting in ${delay / 1000}s (attempt ${this.reconnectAttempt})...`);
    this.reconnectTimer = setTimeout(() => {
      if (this.shouldReconnect) this._connect();
    }, delay);
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (!this.socket) return;
    this.socket.close();
    this.socket = null;
  }

  send(message: SocketMessage): boolean {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return false;
    }
    this.socket.send(JSON.stringify(message));
    return true;
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => {
      this.messageHandlers.delete(handler);
    };
  }

  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  private parseMessage(raw: unknown): SocketMessage | null {
    if (typeof raw !== "string") {
      return null;
    }

    try {
      const parsed = JSON.parse(raw) as SocketMessage;
      if (!parsed || typeof parsed.type !== "string" || parsed.type.length === 0) {
        return null;
      }
      return parsed;
    } catch {
      return null;
    }
  }
}
