import { AppServer } from '@mentra/sdk';
import 'dotenv/config';

class MementoApp extends AppServer {
  
  async onSession(session, sessionId, userId) {
    console.log(`New session started: ${sessionId} for user: ${userId}`);
    
    const frontendUrl = process.env.FRONTEND_URL || 'http://localhost:3000';
    
    session.layouts.showWebView(frontendUrl);
    
    session.events.onTranscription((data) => {
      const text = data.text.toLowerCase();
      console.log(`User said: ${text}`);
      
      if (text.includes('identify') || text.includes('who is') || text.includes('recognize')) {
        this.captureAndIdentify(session);
      } else if (text.includes('home') || text.includes('menu')) {
        session.layouts.showWebView(frontendUrl);
      }
    });
  }
  
  async captureAndIdentify(session) {
    try {
      session.layouts.showTextWall("Scanning...");
      
      const imageData = await session.camera.takePhoto();
      const result = await this.recognizeFace(imageData);
      
      if (result && result.matches && result.matches.length > 0) {
        const match = result.matches[0];
        session.layouts.showTextWall(
          `${match.full_name}\n\n${match.headline || ''}\n\nConfidence: ${Math.round(match.confidence * 100)}%`
        );
      } else {
        session.layouts.showTextWall("No match found\n\nPerson may not be registered");
      }
      
      setTimeout(() => {
        session.layouts.showWebView(process.env.FRONTEND_URL || 'http://localhost:3000');
      }, 5000);
      
    } catch (error) {
      console.error('Recognition error:', error);
      session.layouts.showTextWall("Error\n\nPlease try again");
    }
  }
  
  async recognizeFace(imageData) {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    
    try {
      const response = await fetch(`${backendUrl}/recognize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageData }),
      });
      
      if (!response.ok) throw new Error(`Backend error: ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Backend API error:', error);
      throw error;
    }
  }
}

const app = new MementoApp({
  packageName: 'memento.app',
  apiKey: process.env.MENTRA_API_KEY,
  serverUrl: process.env.MENTRA_SERVER_URL,
  port: parseInt(process.env.PORT || '3001'),
});

console.log('Starting Memento app...');
console.log(`Server: ${process.env.MENTRA_SERVER_URL}`);
console.log(`Frontend: ${process.env.FRONTEND_URL}`);

app.start();
console.log(`Memento app running on port ${process.env.PORT || 3001}`);
