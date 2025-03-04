import { Message } from "../types";

// Backend API URL - change this to your Flask backend URL when deployed
const API_URL = "http://localhost:5000/api";

// Function to send a message to the backend API
export const sendMessage = async (messages: Message[]): Promise<string> => {
  try {
    // Get the last message (user's input)
    const userMessage = messages[messages.length - 1];
    
    // Find or create a conversation ID
    // In a real app, you'd store this in state or localStorage
    const conversationId = localStorage.getItem('conversationId') || '';
    
    // Call the backend API
    const response = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        conversationId,
        message: userMessage.content,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Store the conversation ID for future requests
    if (data.conversationId) {
      localStorage.setItem('conversationId', data.conversationId);
    }
    
    return data.message.content;
  } catch (error) {
    console.error("Error sending message to backend:", error);
    throw new Error("Failed to get response from AI service");
  }
};

// This is a placeholder function that would normally log messages
// In a real implementation, all message storage is handled by the backend
export const storeMessageInGetzep = async (message: Message): Promise<void> => {
  // In a production app, we wouldn't need this function at all
  // as the backend handles all Getzep interactions
  console.log("Message will be stored by backend:", message.id);
};