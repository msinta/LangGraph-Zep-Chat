# Chat Bot Backend

This is the backend for the Chat Bot application, built with Flask and integrated with OpenAI and Getzep.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure environment variables:
   - Copy `.env.example` to `.env` (if it exists)
   - Add your OpenAI API key: `OPENAI_API_KEY=your_openai_api_key_here`
   - Add your Getzep API URL: `GETZEP_API_URL=your_getzep_api_url_here`

3. Run the server:
   ```
   python app.py
   ```

## API Endpoints

### POST /api/chat
Send a message to the chat bot and get a response.

**Request Body:**
```json
{
  "conversationId": "optional-conversation-id",
  "message": "Your message here"
}
```

**Response:**
```json
{
  "conversationId": "conversation-id",
  "message": {
    "id": "message-id",
    "role": "assistant",
    "content": "AI response",
    "timestamp": "2023-01-01T12:00:00.000Z"
  }
}
```

### GET /api/conversations/:conversationId
Get all messages in a conversation.

**Response:**
```json
{
  "conversationId": "conversation-id",
  "messages": [
    {
      "id": "message-id",
      "role": "user",
      "content": "User message",
      "timestamp": "2023-01-01T12:00:00.000Z"
    },
    {
      "id": "message-id",
      "role": "assistant",
      "content": "AI response",
      "timestamp": "2023-01-01T12:00:00.000Z"
    }
  ]
}
```

## Getzep Integration

The application includes a `GetzepClient` class in `getzep_client.py` that provides methods for interacting with the Getzep API. In the current implementation, this integration is a placeholder and would need to be completed based on the actual Getzep API documentation.