import { AppServer } from '@mentra/sdk';
import 'dotenv/config';

import { SocketServer } from './webSocketServer.ts';

type AppServerConfig = ConstructorParameters<typeof AppServer>[0];

class MementoApp extends AppServer {
  private readonly socketServer: SocketServer;
  private websocketStarted = false;

  constructor(config: AppServerConfig) {
    super(config);
    const wsPort = Number.parseInt(process.env.WS_PORT ?? '8080', 10);
    this.socketServer = new SocketServer(Number.isNaN(wsPort) ? 8080 : wsPort);
  }

  async onSession(session: any, sessionId: string, userId: string): Promise<void> {
    console.log(`Session initialized: ${sessionId} for user: ${userId}`);

    const frontendUrl = process.env.FRONTEND_URL || 'http://localhost:3000';
    session.layouts.showWebView(frontendUrl);

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
  port: Number.parseInt(process.env.PORT || '3001', 10),
});

console.log('Starting Memento app...');
console.log(`Frontend: ${process.env.FRONTEND_URL}`);

app.start();
console.log(`Memento app running on port ${process.env.PORT || 3001}`);
