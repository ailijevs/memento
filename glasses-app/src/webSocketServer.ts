import { createServer, IncomingMessage, Server as HttpServer } from 'http';
import { randomUUID } from 'crypto';
import { WebSocketServer, WebSocket } from 'ws';

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

export type IncomingSocketMessage = {
  type: string;
  payload?: JsonValue;
};

type ClientSession = {
  id: string;
  socket: WebSocket;
};

/** WebSocket server wrapper with basic connection/session management. */
export class SocketServer {
  private readonly port: number;
  private readonly httpServer: HttpServer;
  private readonly wsServer: WebSocketServer;
  private readonly clients = new Map<string, ClientSession>();

  constructor(port = 8080) {
    this.port = port;
    this.httpServer = createServer();
    this.wsServer = new WebSocketServer({ server: this.httpServer });

    this.wsServer.on('connection', (socket, request) => {
      this.handleConnection(socket, request);
    });
  }

  /** Start listening for websocket connections on the configured port. */
  start(): Promise<void> {
    return new Promise((resolve) => {
      this.httpServer.listen(this.port, () => {
        console.log(`WebSocket server listening on ws://localhost:${this.port}`);
        resolve();
      });
    });
  }

  /** Stop accepting new connections and close active websocket/http servers. */
  stop(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.wsServer.close((wsError) => {
        if (wsError) {
          reject(wsError);
          return;
        }
        this.httpServer.close((httpError) => {
          if (httpError) {
            reject(httpError);
            return;
          }
          this.clients.clear();
          resolve();
        });
      });
    });
  }

  /** Send a JSON message to one connected client by ID. */
  sendToClient(clientId: string, message: IncomingSocketMessage): boolean {
    const session = this.clients.get(clientId);
    if (!session || session.socket.readyState !== WebSocket.OPEN) {
      return false;
    }
    session.socket.send(JSON.stringify(message));
    return true;
  }

  /** Send a JSON message to every currently connected client. */
  broadcast(message: IncomingSocketMessage): void {
    const serialized = JSON.stringify(message);
    // Pre-serialize once to avoid repeated JSON work in the loop.
    for (const session of this.clients.values()) {
      if (session.socket.readyState === WebSocket.OPEN) {
        session.socket.send(serialized);
      }
    }
  }

  /** Register event handlers for a newly connected websocket client. */
  private handleConnection(socket: WebSocket, request: IncomingMessage): void {
    const clientId = randomUUID();
    this.clients.set(clientId, { id: clientId, socket });
    console.log(`Client connected ${clientId} from ${request.socket.remoteAddress ?? 'unknown'}`);

    socket.send(
      JSON.stringify({
        type: 'connected',
        payload: { clientId },
      } satisfies IncomingSocketMessage),
    );

    socket.on('message', (rawData) => {
      const message = this.parseMessage(rawData.toString());
      if (!message) {
        socket.send(
          JSON.stringify({
            type: 'error',
            payload: { reason: 'invalid_message_format' },
          } satisfies IncomingSocketMessage),
        );
        return;
      }

      console.log(`Message from ${clientId}:`, message);
      socket.send(
        JSON.stringify({
          type: 'ack',
          payload: { receivedType: message.type },
        } satisfies IncomingSocketMessage),
      );
    });

    socket.on('close', () => {
      this.clients.delete(clientId);
      console.log(`Client disconnected ${clientId}`);
    });

    socket.on('error', (error) => {
      console.error(`Socket error for ${clientId}:`, error);
    });
  }

  /** Parse and minimally validate inbound websocket JSON payloads. */
  private parseMessage(raw: string): IncomingSocketMessage | null {
    try {
      const parsed = JSON.parse(raw) as IncomingSocketMessage;
      if (!parsed || typeof parsed.type !== 'string' || parsed.type.length === 0) {
        return null;
      }
      return parsed;
    } catch {
      return null;
    }
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const port = Number.parseInt(process.env.WS_PORT ?? '8080', 10);
  const server = new SocketServer(Number.isNaN(port) ? 8080 : port);
  server.start().catch((error) => {
    console.error('Failed to start websocket server:', error);
    process.exit(1);
  });
}
