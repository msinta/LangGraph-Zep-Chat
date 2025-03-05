import React, { useState, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import { MessageSquare } from "lucide-react";
import ChatHistory from "./components/ChatHistory";
import ChatInput from "./components/ChatInput";
import { Message, ChatState } from "./types";
import { sendMessage } from "./services/chatService";

// Import unique-names-generator
import {
  uniqueNamesGenerator,
  adjectives,
  animals,
} from "unique-names-generator";

function generateFunName(): string {
  return uniqueNamesGenerator({
    dictionaries: [adjectives, animals], // e.g. "big-dog"
    separator: "-",
    style: "lowerCase",
    length: 2,
  });
}

function App() {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    error: null,
  });

  const [userId, setUserId] = useState<string>("");
  const [conversationId, setConversationId] = useState<string>("");

  /**
   * On component mount:
   *  1) Check localStorage for an existing userId, else create one (using unique-names-generator).
   *  2) ALWAYS create a new conversationId, so each refresh is a fresh session.
   */
  useEffect(() => {
    // 1) Load or create userId
    const storedUserId = localStorage.getItem("userId");
    if (storedUserId) {
      setUserId(storedUserId);
    } else {
      const newUserId = generateFunName(); // e.g. "happy-cat"
      setUserId(newUserId);
      localStorage.setItem("userId", newUserId);
    }

    // 2) Always create a new conversationId on mount
    const newConvId = uuidv4();
    setConversationId(newConvId);
  }, []);

  /**
   * Create a brand-new user. This will:
   *  1) Generate a new userId (fun name)
   *  2) Clear the chat messages
   *  3) Generate a new conversationId (UUID)
   */
  const handleCreateNewUser = () => {
    const newUserId = generateFunName(); // e.g. "fancy-horse"
    localStorage.setItem("userId", newUserId);
    setUserId(newUserId);

    // Clear messages
    setChatState({
      messages: [],
      isLoading: false,
      error: null,
    });

    // Also create a fresh conversationId
    const newConvId = uuidv4();
    setConversationId(newConvId);
  };

  /**
   * Send a message to the backend.
   */
  const handleSendMessage = async (content: string) => {
    // Create a new user message
    const userMessage: Message = {
      id: uuidv4(),
      role: "user",
      content,
      timestamp: new Date(),
    };

    // Optimistically update state with the user message
    setChatState((prevState) => ({
      ...prevState,
      messages: [...prevState.messages, userMessage],
      isLoading: true,
      error: null,
    }));

    try {
      // Call the backend service with userId, conversationId, and the user message
      const { newConversationId, aiContent } = await sendMessage({
        userId,
        conversationId,
        message: content,
      });

      // If the backend returns a conversationId (like if it changed),
      // we can update it in state. But we do NOT store it in localStorage.
      if (newConversationId && newConversationId !== conversationId) {
        setConversationId(newConversationId);
      }

      // Create a new assistant message
      const assistantMessage: Message = {
        id: uuidv4(),
        role: "assistant",
        content: aiContent,
        timestamp: new Date(),
      };

      // Update state with the assistant message
      setChatState((prevState) => ({
        ...prevState,
        messages: [...prevState.messages, assistantMessage],
        isLoading: false,
      }));
    } catch (error) {
      console.error("Error in chat:", error);
      setChatState((prevState) => ({
        ...prevState,
        isLoading: false,
        error: "Failed to get a response. Please try again.",
      }));
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      <header className="bg-white shadow-sm p-4">
        <div className="container mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <MessageSquare className="text-blue-500" size={24} />
            <h1 className="text-xl font-semibold text-gray-800">AI Chat Bot</h1>
          </div>
          {/* Display current user & session info */}
          <div className="flex items-center space-x-4">
            {/* User badge */}
            <div className="flex items-center space-x-1">
              <span className="text-gray-500 text-sm">User:</span>
              <span className="inline-block bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded-full">
                {userId}
              </span>
            </div>

            {/* Session badge */}
            <div className="flex items-center space-x-1">
              <span className="text-gray-500 text-sm">Session:</span>
              <span className="inline-block bg-green-100 text-green-800 text-xs font-medium px-2 py-1 rounded-full">
                {conversationId || "none"}
              </span>
            </div>

            {/* Create New User button */}
            <button
              onClick={handleCreateNewUser}
              className="bg-blue-500 hover:bg-blue-600 text-white text-sm px-3 py-1.5 rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
            >
              Create New User
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 container mx-auto max-w-4xl flex flex-col bg-white shadow-md my-4 rounded-lg overflow-hidden">
        <ChatHistory
          messages={chatState.messages}
          isLoading={chatState.isLoading}
        />

        {chatState.error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 mx-4 mb-4 rounded">
            <p>{chatState.error}</p>
          </div>
        )}

        <ChatInput
          onSendMessage={handleSendMessage}
          isLoading={chatState.isLoading}
        />
      </main>

      <footer className="bg-white p-4 shadow-sm">
        <div className="container mx-auto text-center text-gray-500 text-sm">
          Powered by Getzep, LangGraph, and OpenAI
        </div>
      </footer>
    </div>
  );
}

export default App;
