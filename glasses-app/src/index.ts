import Mentra from '@mentra/sdk';
import type { AppSession } from '@mentra/sdk';
import { createServer } from 'http';
import 'dotenv/config';

const { AppServer } = Mentra;

import { BackendClient } from './backendClient.ts';
import { RecognitionController } from './recognitionController.ts';
import { SocketServer } from './webSocketServer.ts';

type AppServerConfig = ConstructorParameters<typeof AppServer>[0];

const port = Number.parseInt(process.env.PORT ?? '3001', 10);
// In production (Railway), share one port for both HTTP and WebSocket.
// Locally, use a separate WS port so the dev server isn't disrupted.
const useSharedPort = !!process.env.PORT;

class MementoApp extends AppServer {
  private readonly socketServer: SocketServer;
  private readonly recognitionController: RecognitionController;
  private websocketStarted = false;
  private activeSession: AppSession | null = null;

  constructor(config: AppServerConfig) {
    super(config);

    if (useSharedPort) {
      // Attach WebSocket to the same HTTP server as Express (single Railway port)
      const httpServer = createServer(this.getExpressApp());
      this.socketServer = new SocketServer(httpServer);
    } else {
      // Local dev: separate WebSocket port
      const wsPort = Number.parseInt(process.env.WS_PORT ?? '8080', 10);
      this.socketServer = new SocketServer(Number.isNaN(wsPort) ? 8080 : wsPort);
    }

    const backendClient = new BackendClient();
    this.recognitionController = new RecognitionController({
      socketServer: this.socketServer,
      backendClient,
      getSession: () => this.activeSession,
    });
    this.socketServer.onMessage((clientId, message) =>
      this.recognitionController.handleSocketCommand(clientId, message),
    );
  }

  override async start(): Promise<void> {
    if (useSharedPort) {
      // Start the shared HTTP server (serves both Express routes and WebSocket)
      const httpServer = (this.socketServer as unknown as { httpServer: ReturnType<typeof createServer> }).httpServer;
      await new Promise<void>((resolve) => {
        httpServer.listen(port, () => {
          console.log(`Memento app running on port ${port} (HTTP + WebSocket)`);
          resolve();
        });
      });
      await this.startWebSocketConnection();
    } else {
      await super.start();
    }
  }

  async onSession(session: AppSession, sessionId: string, userId: string): Promise<void> {
    console.log(`Session initialized: ${sessionId} for user: ${userId}`);
    this.activeSession = session;
    await this.startWebSocketConnection();
  }

  private async startWebSocketConnection(): Promise<void> {
    if (this.websocketStarted) {
      return;
    }
    await this.socketServer.start();
    this.websocketStarted = true;
  }
}

const app = new MementoApp({
  packageName: 'memento-app',
  apiKey: process.env.MENTRA_API_KEY || '',
  port,
});

console.log('Starting Memento app...');
app.start();
