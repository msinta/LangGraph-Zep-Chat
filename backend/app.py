from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
from datetime import datetime
import logging
from dotenv import load_dotenv
from langchain.schema import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from zep_cloud.client import Zep
from zep_cloud import Message

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

print("OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))

chat_model = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

zep_client = Zep(api_key=os.environ.get("ZEP_API_KEY"))

messages_db = {}
conversation_metadata = {}

def ensure_zep_session(conversation_id: str):
    """
    Ensure a Zep session exists for a given conversation.

    If no session exists for the conversation_id, this function creates a new user
    and session in Zep Cloud. If the session already exists, it logs the event and
    updates local metadata with the existing session details.

    Args:
        conversation_id (str): The unique identifier for the conversation.

    Returns:
        None
    """
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    if conversation_id not in conversation_metadata:
        user_name = "User"
        user_id = user_name + str(uuid.uuid4())[:4]
        session_id = conversation_id

        try:
            zep_client.user.add(
                user_id=user_id,
                email=f"{user_name.lower()}@example.com",
                first_name=user_name,
                last_name="Demo"
            )
            zep_client.memory.add_session(
                user_id=user_id,
                session_id=session_id,
            )
            logger.info(f"Created Zep session: user_id={user_id}, session_id={session_id}")
        except Exception as e:
            error_msg = str(e)
            if "session already exists" in error_msg.lower():
                logger.info(f"Session {session_id} already exists; using existing session.")
            else:
                logger.error(f"Error setting up Zep session: {error_msg}")
                return
        conversation_metadata[conversation_id] = {
            "user_id": user_id,
            "session_id": session_id
        }

def store_message_in_zep(message: dict, conversation_id: str):
    """
    Store a message in Zep Cloud using the Zep SDK.

    This function ensures that a valid Zep session exists for the provided conversation,
    then converts the message dictionary into a Zep Message object (including the required
    role_type field) and stores it using the memory client.

    Args:
        message (dict): A dictionary containing message details (role, content, etc.).
        conversation_id (str): The unique identifier for the conversation.

    Returns:
        None
    """
    try:
        ensure_zep_session(conversation_id)
        session_data = conversation_metadata.get(conversation_id)
        if not session_data:
            logger.error("No Zep session metadata found.")
            return

        session_id = session_data["session_id"]

        msg_obj = Message(
            role=message["role"],
            role_type=message["role"],
            content=message["content"]
        )
        result = zep_client.memory.add(session_id, messages=[msg_obj])
        if result:
            logger.info(f"Stored message {message['id']} in Zep session {session_id}")
        else:
            logger.error(f"Failed to store message {message['id']} in Zep.")
    except Exception as e:
        logger.error(f"Error storing message in Zep: {str(e)}")

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handle a chat message and generate an AI response.

    This endpoint accepts a JSON payload with an optional conversationId and a user message.
    It creates a new conversation if needed, stores the user message locally and in Zep Cloud,
    retrieves a response from the OpenAI chat model, stores the AI response, and returns the response.

    Returns:
        JSON: A JSON response containing the conversationId and the AI response message.
    """
    try:
        data = request.json
        conversation_id = data.get('conversationId') or str(uuid.uuid4())
        user_message = data.get('message', '')

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        if conversation_id not in messages_db:
            messages_db[conversation_id] = []
            ensure_zep_session(conversation_id)

        user_msg = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        }
        messages_db[conversation_id].append(user_msg)
        store_message_in_zep(user_msg, conversation_id)

        langchain_messages = []
        for msg in messages_db[conversation_id]:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            else:
                langchain_messages.append(AIMessage(content=msg["content"]))

        ai_response = chat_model.invoke(langchain_messages)

        ai_msg = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": ai_response.content,
            "timestamp": datetime.now().isoformat()
        }
        messages_db[conversation_id].append(ai_msg)
        store_message_in_zep(ai_msg, conversation_id)
        print("AI message:", ai_msg)

        return jsonify({
            "conversationId": conversation_id,
            "message": ai_msg
        })

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """
    Retrieve a conversation's messages and context.

    This endpoint attempts to fetch conversation data from Zep Cloud using the session ID.
    If unsuccessful, it falls back to a locally stored conversation.

    Args:
        conversation_id (str): The unique identifier for the conversation.

    Returns:
        JSON: A JSON response containing the conversation's messages and context, or an error message.
    """
    try:
        if conversation_id in conversation_metadata:
            session_id = conversation_metadata[conversation_id]["session_id"]
            conversation = zep_client.memory.get(session_id)
            if conversation:
                return jsonify({
                    "conversationId": conversation_id,
                    "messages": conversation.get("messages", []),
                    "context": conversation.get("context", "")
                })
        if conversation_id in messages_db:
            return jsonify({
                "conversationId": conversation_id,
                "messages": messages_db[conversation_id]
            })
        else:
            return jsonify({"error": "Conversation not found"}), 404

    except Exception as e:
        logger.error(f"Error retrieving conversation: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
