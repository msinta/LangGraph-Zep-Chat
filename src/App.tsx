import React, { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { MessageSquare } from 'lucide-react';
import ChatHistory from './components/ChatHistory';
import ChatInput from './components/ChatInput';
import { Message, ChatState } from './types';
import { sendMessage } from './services/chatService';

function App() {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    error: null,
  });

  const handleSendMessage = async (content: string) => {
    // Create a new user message
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    // Update state with the user message
    setChatState((prevState) => ({
      ...prevState,
      messages: [...prevState.messages, userMessage],
      isLoading: true,
      error: null,
    }));

    try {
      // Get all messages to send to the API
      const allMessages = [...chatState.messages, userMessage];

      // Send the message to the backend API
      const aiResponse = await sendMessage(allMessages);

      // Create a new assistant message
      const assistantMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: aiResponse,
        timestamp: new Date(),
      };

      // Update state with the assistant message
      setChatState((prevState) => ({
        ...prevState,
        messages: [...prevState.messages, assistantMessage],
        isLoading: false,
      }));
    } catch (error) {
      console.error('Error in chat:', error);
      setChatState((prevState) => ({
        ...prevState,
        isLoading: false,
        error: 'Failed to get a response. Please try again.',
      }));
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      <header className="bg-white shadow-sm p-4">
        <div className="container mx-auto flex items-center">
          <MessageSquare className="text-blue-500 mr-2" size={24} />
          <h1 className="text-xl font-semibold text-gray-800">AI Chat Bot</h1>
        </div>
      </header>

      <main className="flex-1 container mx-auto max-w-4xl flex flex-col bg-white shadow-md my-4 rounded-lg overflow-hidden">
        <ChatHistory messages={chatState.messages} isLoading={chatState.isLoading} />

        {chatState.error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 mx-4 mb-4 rounded">
            <p>{chatState.error}</p>
          </div>
        )}

        <ChatInput onSendMessage={handleSendMessage} isLoading={chatState.isLoading} />
      </main>

      <footer className="bg-white p-4 shadow-sm">
        <div className="container mx-auto text-center text-gray-500 text-sm">
          Powered by Getzep, LangChain, and OpenAI
        </div>
      </footer>
    </div>
  );
}

export default App;
