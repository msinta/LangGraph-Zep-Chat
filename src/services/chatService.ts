const API_URL = "http://localhost:5000/api";

interface SendMessageParams {
  userId: string;
  conversationId: string;
  message: string;
  groupName: string; // <--- new
}

interface SendMessageResponse {
  newConversationId: string;
  aiContent: string;
}

export const sendMessage = async ({
  userId,
  conversationId,
  message,
  groupName, // <--- new
}: SendMessageParams): Promise<SendMessageResponse> => {
  try {
    const response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        userId,
        conversationId,
        message,
        groupName, // <--- new
      }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();
    return {
      newConversationId: data.conversationId,
      aiContent: data.message.content,
    };
  } catch (error) {
    console.error("Error sending message to backend:", error);
    throw new Error("Failed to get response from AI service");
  }
};
