import type { AppSession } from '@mentra/sdk';

import { BackendClient, type FrameDetectionResponse } from './backendClient.ts';
import { IncomingSocketMessage, SocketServer } from './webSocketServer.ts';

type RecognitionCommand = 'start_recognition' | 'stop_recognition';
import 'dotenv/config';

type StartRecognitionPayload = {
  event_id?: string;
};

export class RecognitionController {
  private readonly socketServer: SocketServer;
  private readonly backendClient: BackendClient;
  private readonly getSession: () => AppSession | null;
  private isRunning = false;
  private activeClientId: string | null = null;

  constructor(params: {
    socketServer: SocketServer;
    backendClient: BackendClient;
    getSession: () => AppSession | null;
  }) {
    this.socketServer = params.socketServer;
    this.backendClient = params.backendClient;
    this.getSession = params.getSession;
  }

  async handleSocketCommand(clientId: string, message: IncomingSocketMessage): Promise<void> {
    const command = message.type as RecognitionCommand;
    if (command === 'start_recognition') {
      const payload = this.parseStartPayload(message.payload);
      await this.startRecognition(clientId, payload);
      return;
    }

    if (command === 'stop_recognition') {
      this.stopRecognition(clientId);
    }
  }

  private async startRecognition(clientId: string, payload: StartRecognitionPayload): Promise<void> {
    if (this.isRunning) {
      this.socketServer.sendToClient(clientId, {
        type: 'recognition_status',
        payload: { status: 'already_running' },
      });
      return;
    }

    const session = this.getSession();
    if (!session) {
      this.socketServer.sendToClient(clientId, {
        type: 'recognition_error',
        payload: { message: 'No active glasses session available.' },
      });
      return;
    }

    this.isRunning = true;
    this.activeClientId = clientId;
    this.socketServer.sendToClient(clientId, {
      type: 'recognition_status',
      payload: { status: 'started' },
    });

    this.runRecognitionLoop(session, payload).catch((error) => {
      this.emitToActiveClient({
        type: 'recognition_error',
        payload: { message: this.toErrorMessage(error) },
      });
      this.isRunning = false;
      this.activeClientId = null;
    });
  }

  private stopRecognition(clientId: string): void {
    if (!this.isRunning) {
      this.socketServer.sendToClient(clientId, {
        type: 'recognition_status',
        payload: { status: 'already_stopped' },
      });
      return;
    }

    this.isRunning = false;
    this.socketServer.sendToClient(clientId, {
      type: 'recognition_status',
      payload: { status: 'stopping' },
    });
  }

  private async runRecognitionLoop(
    session: AppSession,
    payload: StartRecognitionPayload,
  ): Promise<void> {
    while (this.isRunning) {
      try {
        const photo = await session.camera.requestPhoto();
        const imageBase64 = photo.buffer.toString('base64');
        // TODO(demo): remove env fallback and pass event_id explicitly from client commands.
        const eventId = payload.event_id ?? process.env.RECOGNITION_EVENT_ID;

        const response: FrameDetectionResponse = await this.backendClient.recognizeFrame({
          image_base64: imageBase64,
          event_id: eventId,
        });

        this.emitToActiveClient({
          type: 'recognition_result',
          payload: {
            timestamp: new Date().toISOString(),
            result: response,
          },
        });
      } catch (error) {
        this.emitToActiveClient({
          type: 'recognition_error',
          payload: { message: this.toErrorMessage(error) },
        });
      }

      await this.sleep(500);
    }

    this.emitToActiveClient({
      type: 'recognition_status',
      payload: { status: 'stopped' },
    });
    this.activeClientId = null;
  }

  private emitToActiveClient(message: IncomingSocketMessage): void {
    if (!this.activeClientId) {
      return;
    }
    this.socketServer.sendToClient(this.activeClientId, message);
  }

  private parseStartPayload(payload: IncomingSocketMessage['payload']): StartRecognitionPayload {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      return {};
    }

    const value = (payload as Record<string, unknown>).event_id;
    if (typeof value !== 'string' || value.trim().length === 0) {
      return {};
    }

    return { event_id: value.trim() };
  }

  private toErrorMessage(error: unknown): string {
    if (error instanceof Error) {
      return error.message;
    }
    return 'Unknown recognition error';
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
