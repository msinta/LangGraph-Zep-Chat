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
from langchain_core.messages import SystemMessage
from pprint import pformat

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

# conversation_metadata:
#   { conversationId -> { "user_id": <userId>, "session_id": <sessionId>, "group_name": <str> } }
conversation_metadata = {}

# messages_db:
#   { conversationId -> [ { "id": <str>, "role": <"user"|"assistant">, "content": <str>, "timestamp": <str> } ] }
messages_db = {}

# -------------------------------------------------
# 2) HELPER FUNCTIONS
# -------------------------------------------------

def ensure_zep_group(group_name: str):
    """Create or reuse a group in Zep."""
    if not group_name:
        return  # no group provided
    try:
        zep_client.group.add(group_id=group_name)
        logger.info(f"Created or re-used group: {group_name}")
    except Exception as e:
        error_msg = str(e).lower()
        if "already exists" in error_msg:
            logger.info(f"Group {group_name} already exists in Zep. Proceeding.")
        else:
            logger.error(f"Error creating group {group_name}: {str(e)}")

def ensure_zep_user_and_session(user_id: str, conversation_id: str):
    """Ensure user & session exist in Zep, store metadata locally."""
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
        "session_id": conversation_id,
        "group_name": "",
    }

def store_message_in_zep(message: dict, conversation_id: str):
    """Store a message in Zep memory for this conversation."""
    session_data = conversation_metadata.get(conversation_id)
    if not session_data:
        logger.error("No Zep session metadata found for conversation %s", conversation_id)
        return

    msg_obj = Message(
        role=message["role"],
        role_type=message["role"],
        content=message["content"]
    )
    try:
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
      - Extract userId, conversationId, groupName, and user message from state.
      - Ensure Zep user & session exist.
      - Ensure the group exists (if groupName is provided).
      - Store user message in local db & Zep.
      - Also add user message to the group graph if groupName is set.
      - Return updated state.
    """
    user_id = state.get("userId") or ""
    conversation_id = state.get("conversationId") or str(uuid.uuid4())
    group_name = state.get("groupName") or ""
    user_message = state.get("message", "")

    if not user_message:
        raise ValueError("Message is required")

    # 1) Ensure user & session in Zep
    ensure_zep_user_and_session(user_id, conversation_id)

    # 2) Ensure group if provided
    if group_name:
        ensure_zep_group(group_name)
        # Store group_name in local metadata
        if conversation_id in conversation_metadata:
            conversation_metadata[conversation_id]["group_name"] = group_name

    # 3) Store user message locally
    if conversation_id not in messages_db:
        messages_db[conversation_id] = []

    user_msg = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat()
    }
    messages_db[conversation_id].append(user_msg)

    # 4) Store user message in Zep
    store_message_in_zep(user_msg, conversation_id)

    # 5) (NEW) Add user message to group graph if groupName is provided
    if group_name:
        try:
            # We store the user message as a text node in the group
            zep_client.graph.add(
                group_id=group_name,
                type="text",
                data=user_message  # store the raw user text
            )
            logger.info(f"Added user message to group {group_name} graph.")
        except Exception as e:
            logger.error(f"Error adding user message to group {group_name}: {str(e)}")

    return {
        "userId": user_id,
        "conversationId": conversation_id,
        "groupName": group_name,
        "messages": messages_db[conversation_id]
    }

def search_zep_history(state: dict, config: RunnableConfig = None) -> dict:
    """
    Node 2:
      - Retrieve conversation context from Zep
      - If groupName is provided, search the group graph for relevant data
      - Attach them to state["found_history"] for generate_response
    """
    conversation_id = state.get("conversationId")
    group_name = state.get("groupName") or ""
    if not conversation_id:
        raise ValueError("No conversationId found in state")

    session_data = conversation_metadata.get(conversation_id)
    if not session_data:
        logger.error(f"No metadata found for conversation {conversation_id}")
        return {**state, "found_history": []}

    session_id = session_data["session_id"]
    user_id = session_data["user_id"]

    found_history = []

    # 1) Retrieve entire conversation from Zep
    try:
        conversation_obj = zep_client.memory.get(session_id)
        if conversation_obj and conversation_obj.messages:
            # Convert each Zep Message into a dict
            for zep_msg in conversation_obj.messages:
                found_history.append({
                    "role_type": zep_msg.role_type,
                    "content": zep_msg.content,
                })
    except Exception as e:
        logger.error(f"Error retrieving conversation from Zep: {str(e)}")

    # 2) Also do a text-based search for relevant group data
    local_messages = state.get("messages", [])
    last_user_content = ""
    for msg in reversed(local_messages):
        if msg["role"] == "user":
            last_user_content = msg["content"]
            break

    if last_user_content.strip() and group_name:
        try:
            results = zep_client.graph.search(
                group_id=group_name,
                query=last_user_content,
                scope="edges"
            )
            if results and results.edges:
                for edge in results.edges:
                    fact_text = getattr(edge, "fact", "Unknown group fact")
                    found_history.append({
                        "role_type": "assistant",
                        "content": f"Group Fact: {fact_text}"
                    })
        except Exception as e:
            logger.error(f"Error searching group graph for {group_name}: {str(e)}")

    return {
        **state,
        "found_history": found_history
    }

def generate_response(state: dict, config: RunnableConfig = None) -> dict:
    """
    Node 3:
      - Combine local messages + found_history
      - Insert found facts as a SystemMessage
      - Call LLM
      - Store AI message
      - Return final { conversationId, message }
    """
    conversation_id = state.get("conversationId")
    found_history = state.get("found_history", [])
    local_messages = state.get("messages", [])

    # 1) Convert found_history from Zep (or group) into AI/user messages
    found_history_msgs = []
    for msg in found_history:
        role = msg.get("role_type", "assistant")
        content = msg.get("content", "")
        if role == "user":
            found_history_msgs.append(HumanMessage(content=content))
        else:
            found_history_msgs.append(AIMessage(content=content))

    # 2) Build a single SystemMessage with all found facts
    facts_text = "\n".join(
        [m.content for m in found_history_msgs if isinstance(m, AIMessage)]
    )
    merged_messages = []

    if facts_text.strip():
        system_msg = SystemMessage(content=f"Relevant facts:\n{facts_text}")
        merged_messages.append(system_msg)

    # 3) Add the user's local messages to the prompt
    for msg in local_messages:
        if msg["role"] == "user":
            merged_messages.append(HumanMessage(content=msg["content"]))
        else:
            merged_messages.append(AIMessage(content=msg["content"]))

    logger.info("Merged messages for LLM prompt:\n%s", pformat(merged_messages, indent=2, width=80))

    # 4) Call LLM
    ai_response = chat_model.invoke(merged_messages)

    # 5) Build & store final AI message
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
        "message": <str>,
        "groupName": <str>   <-- new
      }

    Steps:
      1) We ensure user+session
      2) We ensure group if provided
      3) We run the graph (handle_user_message -> search_zep_history -> generate_response)

    Returns:
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
        conversation_id = payload.get("conversationId") or str(uuid.uuid4())

        group_name = payload.get("groupName", "")
        payload["groupName"] = group_name

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
                    "messages": conversation.messages,  # or convert them to dict if needed
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
