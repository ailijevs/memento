import Mentra from '@mentra/sdk';
import type { AppSession } from '@mentra/sdk';
import { createServer, type Server as HttpServer } from 'http';
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
  private socketServer: SocketServer;
  private readonly recognitionController: RecognitionController;
  private websocketStarted = false;
  private activeSession: AppSession | null = null;

  constructor(config: AppServerConfig) {
    super(config);

    // Local dev: start with a standalone WebSocket port
    const wsPort = Number.parseInt(process.env.WS_PORT ?? '8080', 10);
    this.socketServer = new SocketServer(Number.isNaN(wsPort) ? 8080 : wsPort);

    const backendClient = new BackendClient();
    this.recognitionController = new RecognitionController({
      getSocketServer: () => this.socketServer,
      backendClient,
      getSession: () => this.activeSession,
    });
    this.socketServer.onMessage((clientId, message) =>
      this.recognitionController.handleSocketCommand(clientId, message),
    );
  }

  override async start(): Promise<void> {
    if (useSharedPort) {
      // Intercept Express's listen call to capture the HTTP server,
      // then attach our WebSocket to it — so both share a single Railway port.
      // super.start() runs in full (MentraOS SDK init included).
      const expressApp = this.getExpressApp();
      let capturedServer: HttpServer | undefined;

      const origListen = expressApp.listen.bind(expressApp);
      (expressApp as unknown as { listen: (...a: unknown[]) => HttpServer }).listen = (...args: unknown[]) => {
        capturedServer = createServer(expressApp);
        (capturedServer as unknown as { listen: (...a: unknown[]) => void }).listen(...args);
        return capturedServer;
      };

      await super.start();

      if (capturedServer) {
        // Replace the standalone WS server with one attached to the shared HTTP server
        this.socketServer = new SocketServer(capturedServer);
        this.socketServer.onMessage((clientId, message) =>
          this.recognitionController.handleSocketCommand(clientId, message),
        );
        await this.startWebSocketConnection();
      }
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
  packageName: 'memento.app',
  apiKey: process.env.MENTRA_API_KEY || '',
  port,
});

console.log('Starting Memento app...');
app.start();
