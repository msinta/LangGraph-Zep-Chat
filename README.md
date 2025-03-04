# AI Chat Bot Frontend

A modern, responsive chat interface built with React, TypeScript, and Tailwind CSS that connects to a Flask backend powered by OpenAI, LangChain, and Getzep.

ScreenShot:
<img width="1533" alt="Screenshot 2025-03-03 at 11 21 21 PM" src="https://github.com/user-attachments/assets/5ca87047-0ae9-452d-a7e2-483cdf841fb3" />


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
- Python 3.8+ and pip (for the backend)

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a Python virtual environment (recommended):
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Configure environment variables:
   - Update the `.env` file in the backend directory:
     ```
   - Add your OpenAI API key: `OPENAI_API_KEY=your_openai_api_key_here`
   - Add your Getzep API URL: `GETZEP_API_URL=your_getzep_api_url_here`
     ```

6. Start the backend server:
   ```bash
   python app.py
   ```

   The backend server will run on `http://localhost:5000` by default.

### Frontend Setup

1. Open a new terminal window and navigate to the project root directory.

2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser and navigate to `http://localhost:5173`

## Project Structure

```
/
├── src/                # Frontend source code
│   ├── components/     # UI components
│   ├── services/       # API services
│   ├── types/          # TypeScript type definitions
│   ├── App.tsx         # Main application component
│   └── main.tsx        # Application entry point
│
└── backend/            # Backend source code
    ├── app.py          # Flask application
    ├── getzep_client.py # Getzep API client
    └── requirements.txt # Python dependencies
```

## API Integration

The frontend communicates with the Flask backend through the following endpoints:

- `POST /api/chat` - Send a message and get an AI response
- `GET /api/conversations/:id` - Retrieve a specific conversation
- `POST /api/search` - Search through conversation history

## Setting Up Getzep

To use Getzep for conversation storage and retrieval:

1. Sign up for a Getzep account at [getzep.com](https://getzep.com) or set up a self-hosted instance
2. Create a new project and obtain your API URL and key
3. Update both the frontend and backend `.env` files with your Getzep credentials
