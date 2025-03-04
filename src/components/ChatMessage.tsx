import React from 'react';
import { Message } from '../types';
import { User, Bot } from 'lucide-react';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`flex max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        <div className={`flex items-center justify-center h-10 w-10 rounded-full ${isUser ? 'bg-blue-500 ml-3' : 'bg-gray-300 mr-3'}`}>
          {isUser ? <User size={20} className="text-white" /> : <Bot size={20} className="text-gray-700" />}
        </div>
        <div className={`py-3 px-4 rounded-lg ${isUser ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-800'}`}>
          <p className="text-sm">{message.content}</p>
          <p className="text-xs mt-1 opacity-70">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;