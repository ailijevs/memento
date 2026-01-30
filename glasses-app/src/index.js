import { AppServer } from '@mentra/sdk';
import 'dotenv/config';

/**
 * Memento - Face Recognition App for MentraOS
 * 
 * This app captures faces through smart glasses and identifies
 * people using the Memento backend API.
 */
class MementoApp extends AppServer {
  
  /**
   * Called when a user starts a session with the app
   */
  async onSession(session, sessionId, userId) {
    console.log(`New session started: ${sessionId} for user: ${userId}`);
    
    // Welcome message
    session.layouts.showTextWall("Memento Ready\n\nSay 'identify' to recognize someone");
    
    // Listen for voice commands
    session.events.onTranscription((data) => {
      const text = data.text.toLowerCase();
      console.log(`User said: ${text}`);
      
      if (text.includes('identify') || text.includes('who is') || text.includes('recognize')) {
        this.captureAndIdentify(session);
      }
    });
    
    // Alternative: trigger on button press or gesture
    // session.events.onTap(() => this.captureAndIdentify(session));
  }
  
  /**
   * Capture photo and send to backend for identification
   */
  async captureAndIdentify(session) {
    try {
      session.layouts.showTextWall("Scanning...");
      
      // Capture image from glasses camera
      const imageData = await session.camera.takePhoto();
      
      // Send to Memento backend for recognition
      const result = await this.recognizeFace(imageData);
      
      if (result && result.matches && result.matches.length > 0) {
        const match = result.matches[0];
        session.layouts.showTextWall(
          `${match.full_name}\n\n${match.headline || ''}\n\nConfidence: ${Math.round(match.confidence * 100)}%`
        );
      } else {
        session.layouts.showTextWall("No match found\n\nPerson may not be registered");
      }
      
      // Reset after 5 seconds
      setTimeout(() => {
        session.layouts.showTextWall("Memento Ready\n\nSay 'identify' to recognize someone");
      }, 5000);
      
    } catch (error) {
      console.error('Recognition error:', error);
      session.layouts.showTextWall("Error\n\nPlease try again");
    }
  }
  
  /**
   * Call Memento backend API to recognize a face
   */
  async recognizeFace(imageData) {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    
    try {
      const response = await fetch(`${backendUrl}/recognize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image: imageData, // Base64 encoded image
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('Backend API error:', error);
      throw error;
    }
  }
}

// Start the app
const app = new MementoApp({
  packageName: 'com.memento.glasses',
  apiKey: process.env.MENTRA_API_KEY,
  port: parseInt(process.env.PORT || '3000'),
});

console.log('Starting Memento glasses app...');
console.log(`Backend URL: ${process.env.BACKEND_URL}`);

app.start();
console.log(`Memento app running on port ${process.env.PORT || 3000}`);
