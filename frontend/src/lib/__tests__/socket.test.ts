import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { SocketClient } from "../socket";

class MockWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  readonly CONNECTING = 0;
  readonly OPEN = 1;
  readonly CLOSING = 2;
  readonly CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  send = vi.fn();
  close = vi.fn();
  protocol = "";
  bufferedAmount = 0;
  extensions = "";
  binaryType: BinaryType = "blob";
  addEventListener = vi.fn();
  removeEventListener = vi.fn();
  dispatchEvent = vi.fn().mockReturnValue(true);

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  static instances: MockWebSocket[] = [];
  static reset() {
    MockWebSocket.instances = [];
  }

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event("open"));
  }

  simulateMessage(data: string) {
    this.onmessage?.(new MessageEvent("message", { data }));
  }

  simulateClose(code = 1000, wasClean = true) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code, wasClean, reason: "" } as CloseEvent);
  }

  simulateError() {
    this.onerror?.(new Event("error"));
  }
}

describe("SocketClient", () => {
  let client: SocketClient;
  const originalWS = globalThis.WebSocket;

  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.reset();
    globalThis.WebSocket = MockWebSocket as unknown as typeof WebSocket;
    client = new SocketClient("ws://test-server:3001");
  });

  afterEach(() => {
    client.disconnect();
    globalThis.WebSocket = originalWS;
    vi.useRealTimers();
  });

  it("creates a WebSocket connection on connect", () => {
    client.connect();
    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toContain("ws://test-server:3001");
  });

  it("includes token in connection URL when provided", () => {
    client.connect("my-auth-token");
    expect(MockWebSocket.instances[0].url).toContain("token=my-auth-token");
  });

  it("does not include token query param when no token", () => {
    client.connect();
    expect(MockWebSocket.instances[0].url).not.toContain("token=");
  });

  it("does not create duplicate connections when already connected", () => {
    client.connect();
    MockWebSocket.instances[0].simulateOpen();
    client.connect();
    expect(MockWebSocket.instances).toHaveLength(1);
  });

  it("does not create duplicate connections when still connecting", () => {
    client.connect();
    client.connect();
    expect(MockWebSocket.instances).toHaveLength(1);
  });

  it("reports isConnected correctly", () => {
    expect(client.isConnected()).toBe(false);
    client.connect();
    expect(client.isConnected()).toBe(false);
    MockWebSocket.instances[0].simulateOpen();
    expect(client.isConnected()).toBe(true);
  });

  it("parses and dispatches valid messages to handlers", () => {
    const handler = vi.fn();
    client.onMessage(handler);
    client.connect();
    MockWebSocket.instances[0].simulateOpen();

    const msg = JSON.stringify({
      type: "connected",
      payload: { clientId: "c1" },
    });
    MockWebSocket.instances[0].simulateMessage(msg);

    expect(handler).toHaveBeenCalledWith({
      type: "connected",
      payload: { clientId: "c1" },
    });
  });

  it("ignores invalid JSON messages", () => {
    const handler = vi.fn();
    client.onMessage(handler);
    client.connect();
    MockWebSocket.instances[0].simulateOpen();
    MockWebSocket.instances[0].simulateMessage("not-json{{{");
    expect(handler).not.toHaveBeenCalled();
  });

  it("ignores messages without a type field", () => {
    const handler = vi.fn();
    client.onMessage(handler);
    client.connect();
    MockWebSocket.instances[0].simulateOpen();
    MockWebSocket.instances[0].simulateMessage(JSON.stringify({ payload: {} }));
    expect(handler).not.toHaveBeenCalled();
  });

  it("ignores messages with empty type", () => {
    const handler = vi.fn();
    client.onMessage(handler);
    client.connect();
    MockWebSocket.instances[0].simulateOpen();
    MockWebSocket.instances[0].simulateMessage(
      JSON.stringify({ type: "", payload: {} })
    );
    expect(handler).not.toHaveBeenCalled();
  });

  it("allows removing a message handler", () => {
    const handler = vi.fn();
    const unsub = client.onMessage(handler);
    unsub();
    client.connect();
    MockWebSocket.instances[0].simulateOpen();
    MockWebSocket.instances[0].simulateMessage(
      JSON.stringify({ type: "ack", payload: { receivedType: "test" } })
    );
    expect(handler).not.toHaveBeenCalled();
  });

  it("send returns true when connected", () => {
    client.connect();
    MockWebSocket.instances[0].simulateOpen();
    const result = client.send({
      type: "start_recognition",
      payload: { event_id: "e1" },
    });
    expect(result).toBe(true);
    expect(MockWebSocket.instances[0].send).toHaveBeenCalledWith(
      JSON.stringify({
        type: "start_recognition",
        payload: { event_id: "e1" },
      })
    );
  });

  it("send returns false when not connected", () => {
    const result = client.send({ type: "stop_recognition" });
    expect(result).toBe(false);
  });

  it("send returns false when socket is connecting", () => {
    client.connect();
    const result = client.send({ type: "stop_recognition" });
    expect(result).toBe(false);
  });

  it("closes the WebSocket on disconnect", () => {
    client.connect();
    MockWebSocket.instances[0].simulateOpen();
    client.disconnect();
    expect(MockWebSocket.instances[0].close).toHaveBeenCalled();
  });

  it("schedules reconnection after unclean close", () => {
    client.connect();
    MockWebSocket.instances[0].simulateOpen();
    MockWebSocket.instances[0].simulateClose(1006, false);

    expect(MockWebSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(2000);
    expect(MockWebSocket.instances).toHaveLength(2);
  });

  it("does not reconnect after explicit disconnect", () => {
    client.connect();
    MockWebSocket.instances[0].simulateOpen();
    client.disconnect();
    MockWebSocket.instances[0].simulateClose(1000, true);

    vi.advanceTimersByTime(30000);
    expect(MockWebSocket.instances).toHaveLength(1);
  });

  it("increases reconnection delay with backoff", () => {
    client.connect();
    MockWebSocket.instances[0].simulateOpen();
    MockWebSocket.instances[0].simulateClose(1006, false);

    vi.advanceTimersByTime(2000);
    expect(MockWebSocket.instances).toHaveLength(2);

    MockWebSocket.instances[1].simulateClose(1006, false);
    vi.advanceTimersByTime(2000);
    expect(MockWebSocket.instances).toHaveLength(2);
    vi.advanceTimersByTime(2000);
    expect(MockWebSocket.instances).toHaveLength(3);
  });

  it("resets reconnection attempt counter on successful open", () => {
    client.connect();
    MockWebSocket.instances[0].simulateOpen();
    MockWebSocket.instances[0].simulateClose(1006, false);

    vi.advanceTimersByTime(2000);
    MockWebSocket.instances[1].simulateOpen();
    MockWebSocket.instances[1].simulateClose(1006, false);

    vi.advanceTimersByTime(2000);
    expect(MockWebSocket.instances).toHaveLength(3);
  });

  it("dispatches to multiple handlers", () => {
    const handler1 = vi.fn();
    const handler2 = vi.fn();
    client.onMessage(handler1);
    client.onMessage(handler2);
    client.connect();
    MockWebSocket.instances[0].simulateOpen();

    MockWebSocket.instances[0].simulateMessage(
      JSON.stringify({ type: "ack", payload: { receivedType: "test" } })
    );

    expect(handler1).toHaveBeenCalledTimes(1);
    expect(handler2).toHaveBeenCalledTimes(1);
  });

  it("catches handler errors without affecting other handlers", async () => {
    const errorHandler = vi.fn().mockRejectedValue(new Error("handler fail"));
    const goodHandler = vi.fn();
    client.onMessage(errorHandler);
    client.onMessage(goodHandler);
    client.connect();
    MockWebSocket.instances[0].simulateOpen();

    MockWebSocket.instances[0].simulateMessage(
      JSON.stringify({ type: "ack", payload: { receivedType: "test" } })
    );

    await vi.advanceTimersByTimeAsync(0);
    expect(goodHandler).toHaveBeenCalledTimes(1);
  });
});
