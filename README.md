# AI Chat Bot Frontend

A modern, responsive chat interface built with React, TypeScript, and Tailwind CSS that connects to a Flask backend powered by OpenAI, LangChain, and Getzep.

![Chat Bot Screenshot](https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?auto=format&fit=crop&q=80&w=1024)

## Features

- 💬 Real-time chat interface with AI assistant
- 🔄 Persistent conversation history
- 📱 Fully responsive design for all devices
- 🎨 Modern UI with Tailwind CSS
- 🔍 Search functionality for past conversations
- 🔒 Secure API integration

## Tech Stack

- **React 18** - Modern UI library
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **Vite** - Next-generation frontend tooling
- **Lucide React** - Beautiful, consistent icons

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- Backend server running (see backend README)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-chat-bot.git
   cd ai-chat-bot
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables:
   - Copy `.env.example` to `.env` (if it exists)
   - Update the environment variables:
     ```
     VITE_OPENAI_API_KEY=your_openai_api_key_here
     VITE_GETZEP_API_URL=your_getzep_api_url_here
     VITE_GETZEP_API_KEY=your_getzep_api_key_here
     ```

4. Start the development server:
   ```bash
   npm run dev
   ```

5. Open your browser and navigate to `http://localhost:5173`

## Project Structure

```
src/
├── components/         # UI components
│   ├── ChatHistory.tsx # Displays message history
│   ├── ChatInput.tsx   # User input component
│   └── ChatMessage.tsx # Individual message component
├── services/           # API services
│   └── chatService.ts  # Handles API communication
├── types/              # TypeScript type definitions
│   └── index.ts        # Shared types
├── App.tsx             # Main application component
└── main.tsx            # Application entry point
```

## API Integration

The frontend communicates with the Flask backend through the following endpoints:

- `POST /api/chat` - Send a message and get an AI response
- `GET /api/conversations/:id` - Retrieve a specific conversation
- `POST /api/search` - Search through conversation history

## Building for Production

To build the application for production:

```bash
npm run build
```

This will generate optimized assets in the `dist` directory that can be deployed to any static hosting service.
