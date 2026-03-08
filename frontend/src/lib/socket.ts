export type SocketMessage = {
  type: string;
  payload?: unknown;
};

type MessageHandler = (message: SocketMessage) => void | Promise<void>;

/**
 * Browser WebSocket client for the glasses-app websocket server.
 * Supports message fan-out to registered handlers.
 */
export class SocketClient {
  private readonly url: string;
  private socket: WebSocket | null = null;
  private readonly messageHandlers = new Set<MessageHandler>();

  constructor(url?: string) {
    this.url = url || process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8080";
  }

  connect(): void {
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

    this.socket.onerror = (event) => {
      console.error("[SocketClient] WebSocket error:", event);
    };

    this.socket.onclose = () => {
      console.log("[SocketClient] Disconnected");
      this.socket = null;
    };
  }

  disconnect(): void {
    if (!this.socket) {
      return;
    }
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
