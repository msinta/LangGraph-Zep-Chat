from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
from datetime import datetime
import logging
from dotenv import load_dotenv

# LangChain & Zep imports
from langchain.schema import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from zep_cloud.client import Zep
from zep_cloud import Message

# LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# -------------------------------------------------
# 1) MODEL, ZEP CLIENT, & LOCAL STORES
# -------------------------------------------------
chat_model = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o",  # or "gpt-4", "gpt-3.5-turbo", etc.
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

zep_client = Zep(api_key=os.getenv("ZEP_API_KEY"))

# Local in-memory structures:
# conversation_metadata:
#   { conversationId -> { "user_id": <userId>, "session_id": <sessionId> } }
conversation_metadata = {}

# messages_db:
#   { conversationId -> [ { "id": <str>, "role": <"user"|"assistant">, "content": <str>, "timestamp": <str> } ] }
messages_db = {}

# -------------------------------------------------
# 2) HELPER FUNCTIONS (ZEP & LOCAL)
# -------------------------------------------------

def ensure_zep_user_and_session(user_id: str, conversation_id: str):
    """
    Ensure the given user_id exists in Zep; create if needed.
    Then ensure conversation_id is a session for that user.
    """
    try:
        zep_client.user.add(
            user_id=user_id,
            email=f"{user_id.lower()}@example.com",
            first_name=user_id,
            last_name="Demo"
        )
        logger.info(f"Created user in Zep: user_id={user_id}")
    except Exception as e:
        error_msg = str(e).lower()
        if "user already exists" in error_msg:
            logger.info(f"User {user_id} already exists in Zep. Proceeding.")
        else:
            logger.error(f"Error creating user {user_id}: {str(e)}")
            return
    try:
        zep_client.memory.add_session(
            user_id=user_id,
            session_id=conversation_id,
        )
        logger.info(f"Created session: conversation_id={conversation_id}")
    except Exception as e:
        error_msg = str(e).lower()
        if "session already exists" in error_msg:
            logger.info(f"Session {conversation_id} already exists for user {user_id}.")
        else:
            logger.error(f"Error creating session {conversation_id}: {str(e)}")
            return

    # Store locally
    conversation_metadata[conversation_id] = {
        "user_id": user_id,
        "session_id": conversation_id
    }


def store_message_in_zep(message: dict, conversation_id: str):
    """
    Store a message in Zep Cloud for the given conversation ID.

    Args:
        message (dict): { "id": <str>, "role": "user"|"assistant", "content": <str>, "timestamp": <str> }
        conversation_id (str): The conversation ID representing a Zep session.

    Side Effects:
        - Looks up user_id & session_id from conversation_metadata
        - Adds the message to Zep's memory for that session
    """
    session_data = conversation_metadata.get(conversation_id)
    if not session_data:
        logger.error("No Zep session metadata found for conversation %s", conversation_id)
        return

    # Build a Zep message object
    msg_obj = Message(
        role=message["role"],
        role_type=message["role"],
        content=message["content"]
    )
    try:
        # Actually store it in Zep
        result = zep_client.memory.add(session_data["session_id"], messages=[msg_obj])
        if result:
            logger.info(f"Stored message {message['id']} in Zep session {session_data['session_id']}")
        else:
            logger.error(f"Failed to store message {message['id']} in Zep.")
    except Exception as e:
        logger.error(f"Error storing message in Zep: {str(e)}")

# -------------------------------------------------
# 3) LANGGRAPH NODES
# -------------------------------------------------

def handle_user_message(state: dict, config: RunnableConfig = None) -> dict:
    """
    Node 1:
      - Extract userId, conversationId, and user message from state.
      - Ensure Zep user & session exist (via ensure_zep_user_and_session).
      - Store user message in local db & Zep.
      - Return updated state for next node.
    """
    user_id = state.get("userId") or ""
    conversation_id = state.get("conversationId") or str(uuid.uuid4())
    user_message = state.get("message", "")

    if not user_message:
        raise ValueError("Message is required")

    print("user_id", user_id)
    print("conversation_id", conversation_id)
    print("user_message", user_message)

    # 1) Ensure user & session in Zep
    ensure_zep_user_and_session(user_id, conversation_id)

    # 2) Store user message locally
    if conversation_id not in messages_db:
        messages_db[conversation_id] = []

    user_msg = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat()
    }
    messages_db[conversation_id].append(user_msg)

    # 3) Store user message in Zep
    store_message_in_zep(user_msg, conversation_id)

    # Return updated state with conversationId & messages
    return {
        "userId": user_id,
        "conversationId": conversation_id,
        "messages": messages_db[conversation_id]
    }

def search_zep_history(state: dict, config: RunnableConfig = None) -> dict:
    """
    Node 2:
      - Retrieve relevant conversation context/facts from Zep
      - e.g. memory.get(session_id)
      - Attach them to state["found_history"]
    """
    conversation_id = state.get("conversationId")
    if not conversation_id:
        raise ValueError("No conversationId found in state")

    found_history = []
    session_data = conversation_metadata.get(conversation_id)
    if session_data:
        session_id = session_data["session_id"]
        try:
            conversation = zep_client.memory.get(session_id)
            if conversation:
                found_history = conversation.get("messages", [])
        except Exception as e:
            logger.error(f"Error retrieving conversation from Zep: {str(e)}")

    return {
        **state,
        "found_history": found_history
    }

def generate_response(state: dict, config: RunnableConfig = None) -> dict:
    """
    Node 3:
      - Combine local messages + found_history
      - Call LLM
      - Store AI message
      - Return final { conversationId, message }
    """
    conversation_id = state.get("conversationId")
    found_history = state.get("found_history", [])
    local_messages = state.get("messages", [])

    # Convert found_history from Zep into LangChain messages
    merged_messages = []
    for msg in found_history:
        role = msg.get("role_type", "assistant")
        content = msg.get("content", "")
        if role == "user":
            merged_messages.append(HumanMessage(content=content))
        else:
            merged_messages.append(AIMessage(content=content))

    # Add local messages to merged
    for msg in local_messages:
        if msg["role"] == "user":
            merged_messages.append(HumanMessage(content=msg["content"]))
        else:
            merged_messages.append(AIMessage(content=msg["content"]))

    # Call LLM
    ai_response = chat_model.invoke(merged_messages)

    # Build & store final AI message
    ai_msg = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": ai_response.content,
        "timestamp": datetime.now().isoformat()
    }
    local_messages.append(ai_msg)
    messages_db[conversation_id] = local_messages
    store_message_in_zep(ai_msg, conversation_id)

    logger.info(f"Final AI message: {ai_msg}")

    return {
        "conversationId": conversation_id,
        "message": ai_msg
    }

# -------------------------------------------------
# 4) BUILD THE GRAPH
# -------------------------------------------------
builder = StateGraph(dict)

builder.add_node("handle_user_message", handle_user_message)
builder.add_node("search_zep_history", search_zep_history)
builder.add_node("generate_response", generate_response)

builder.add_edge(START, "handle_user_message")
builder.add_edge("handle_user_message", "search_zep_history")
builder.add_edge("search_zep_history", "generate_response")
builder.add_edge("generate_response", END)

memory_saver = MemorySaver()
graph = builder.compile(checkpointer=memory_saver)

# -------------------------------------------------
# 5) FLASK ENDPOINTS
# -------------------------------------------------
@app.route('/api/chat', methods=['POST'])
def chat():
    """
    POST /api/chat

    Expects JSON with:
      {
        "userId": <str>,
        "conversationId": <str>,
        "message": <str>
      }

    If userId is new, the code will create that user in Zep.
    If conversationId is new, the code will create a new session in Zep for that user.
    Then it runs the graph, which:
      - handle_user_message
      - search_zep_history
      - generate_response
    and returns the final AI message.

    Returns JSON:
      {
        "conversationId": <str>,
        "message": {
          "id": <str>,
          "role": "assistant",
          "content": <str>,
          "timestamp": <str>
        }
      }
    """
    try:
        payload = request.json or {}
        # For memory saver, we still need a "thread_id"
        # We can use conversationId or userId, or both
        conversation_id = payload.get("conversationId") or str(uuid.uuid4())

        result = graph.invoke(
            payload,
            config={"configurable": {"thread_id": conversation_id}}
        )
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation_route(conversation_id):
    """
    GET /api/conversations/<conversation_id>

    Retrieves the conversation from Zep or local fallback.
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
