import { AppServer } from '@mentra/sdk';
import 'dotenv/config';

class MementoApp extends AppServer {

  async onSession(session, sessionId, userId) {
    console.log(`New session started: ${sessionId} for user: ${userId}`);

    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    // Show idle state on glasses display
    session.layouts.showTextWall("Memento\n\nPress button to start scanning");

    // Physical button (short press) → toggle capture on/off
    session.events.onButtonPress(async (data) => {
      if (data.pressType !== 'short') return;
      try {
        const res = await fetch(`${backendUrl}/api/v1/capture/toggle/${userId}`, {
          method: 'POST',
        });
        const { capturing } = await res.json();
        session.layouts.showTextWall(
          capturing ? "Memento\n\nScanning..." : "Memento\n\nScanning stopped"
        );
        if (!capturing) {
          setTimeout(() => {
            session.layouts.showTextWall("Memento\n\nPress button to start scanning");
          }, 2000);
        }
      } catch (err) {
        console.error('Toggle error:', err);
      }
    });

    // Voice commands still work
    session.events.onTranscription((data) => {
      const text = data.text.toLowerCase();
      console.log(`User said: ${text}`);

      if (text.includes('identify') || text.includes('who is') || text.includes('recognize')) {
        this.captureAndIdentify(session, backendUrl);
      } else if (text.includes('stop')) {
        fetch(`${backendUrl}/api/v1/capture/toggle/${userId}`, { method: 'POST' })
          .then(r => r.json())
          .then(({ capturing }) => {
            if (!capturing) session.layouts.showTextWall("Memento\n\nScanning stopped");
          })
          .catch(console.error);
      }
    });

    // Poll capture state every 3s — auto-capture when active
    let isCapturing = false;
    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`${backendUrl}/api/v1/capture/state/${userId}`);
        if (!res.ok) return;
        const { capturing } = await res.json();
        if (capturing && !isCapturing) {
          isCapturing = true;
          await this.captureAndIdentify(session, backendUrl);
          isCapturing = false;
        }
      } catch { /* ignore */ }
    }, 500);

    session.events.onSessionEnd?.(() => clearInterval(pollInterval));
  }

  async captureAndIdentify(session, backendUrl) {
    try {
      session.layouts.showTextWall("Scanning...");

      const photo = await session.camera.requestPhoto();
      const result = await this.recognizeFace(photo, backendUrl);

      if (result && result.matches && result.matches.length > 0) {
        const match = result.matches[0];
        session.layouts.showTextWall(
          `${match.full_name}\n${match.headline || ''}\n\nConfidence: ${Math.round(match.confidence * 100)}%`
        );
      } else {
        session.layouts.showTextWall("No match found");
      }

      // Return to scanning state after showing result
      await new Promise(r => setTimeout(r, 4000));
      session.layouts.showTextWall("Memento\n\nScanning...");

    } catch (error) {
      console.error('Recognition error:', error);
      session.layouts.showTextWall("Error\n\nPlease try again");
    }
  }

  async recognizeFace(photo, backendUrl) {
    // Convert ArrayBuffer photo data to base64
    const buffer = Buffer.from(photo.photoData);
    const base64 = buffer.toString('base64');

    const response = await fetch(`${backendUrl}/recognize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: base64, mime_type: photo.mimeType }),
    });

    if (!response.ok) throw new Error(`Backend error: ${response.status}`);
    return response.json();
  }
}

const app = new MementoApp({
  packageName: 'memento.app',
  apiKey: process.env.MENTRA_API_KEY,
  serverUrl: process.env.MENTRA_SERVER_URL,
  port: parseInt(process.env.PORT || '3001'),
});

console.log('Starting Memento app...');
app.start();
console.log(`Memento app running on port ${process.env.PORT || 3001}`);
