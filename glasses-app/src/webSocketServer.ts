import { createServer, IncomingMessage, Server as HttpServer } from 'http';
import { randomUUID } from 'crypto';
import { WebSocketServer, WebSocket } from 'ws';

export type IncomingSocketMessage = {
  type: string;
  payload?: unknown;
};

type ClientSession = {
  id: string;
  socket: WebSocket;
};

type MessageHandler = (clientId: string, message: IncomingSocketMessage) => void | Promise<void>;

/** WebSocket server wrapper with basic connection/session management. */
export class SocketServer {
  private readonly port: number;
  private readonly httpServer: HttpServer;
  private readonly ownHttpServer: boolean;
  private readonly wsServer: WebSocketServer;
  private readonly clients = new Map<string, ClientSession>();
  private readonly messageHandlers = new Set<MessageHandler>();

  constructor(portOrServer: number | HttpServer = 8080) {
    if (typeof portOrServer === 'number') {
      this.port = portOrServer;
      this.httpServer = createServer();
      this.ownHttpServer = true;
    } else {
      this.port = 0;
      this.httpServer = portOrServer;
      this.ownHttpServer = false;
    }
    this.wsServer = new WebSocketServer({ server: this.httpServer });

    this.wsServer.on('connection', (socket, request) => {
      this.handleConnection(socket, request);
    });
  }

  /** Start listening for websocket connections. If using a shared HTTP server, it is already listening. */
  start(): Promise<void> {
    if (!this.ownHttpServer) {
      console.log(`WebSocket server attached to shared HTTP server`);
      return Promise.resolve();
    }
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

  /** Register a callback for inbound client messages. */
  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => {
      this.messageHandlers.delete(handler);
    };
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

      for (const handler of this.messageHandlers) {
        Promise.resolve(handler(clientId, message)).catch((error) => {
          console.error(`Message handler error for ${clientId}:`, error);
        });
      }
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
