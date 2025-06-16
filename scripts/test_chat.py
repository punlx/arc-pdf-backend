import requests

BASE_URL = "http://localhost:8000"


def test_create_chat():
    """Test creating a new chat session"""
    print("💬 Testing Create Chat...")

    try:
        response = requests.post(f"{BASE_URL}/api/chat/create")
        response.raise_for_status()

        data = response.json()
        print(f"✅ Chat created: {data['message']}")
        print(f"   Chat ID: {data['chat_id']}")

        assert "chat_id" in data
        assert data["message"] == "New chat session created successfully"
        return data["chat_id"]

    except Exception as e:
        print(f"❌ Create chat failed: {e}")
        return None


def test_send_chat_message(chat_id=None):
    """Test sending a chat message"""
    print("\n💬 Testing Send Chat Message...")

    try:
        payload = {
            "question": "What are the main findings about text-to-SQL capabilities discussed in the uploaded documents?"
        }

        if chat_id:
            payload["chat_id"] = chat_id
            print(f"   Using chat ID: {chat_id}")

        response = requests.post(
            f"{BASE_URL}/api/chat",
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        print("✅ Message sent successfully")
        print(f"   Question: {data['answer'][:100]}...")
        print(f"   Source: {data['source']}")
        print(f"   Message ID: {data['id']}")
        print(f"   Chat ID: {data['chat_id']}")
        print(f"   Timestamp: {data['timestamp']}")

        assert "answer" in data
        assert "chat_id" in data
        return data

    except Exception as e:
        print(f"❌ Send chat message failed: {e}")
        return None


def test_get_chat_history(chat_id):
    """Test getting chat history for a specific chat"""
    print("\n💬 Testing Get Chat History...")

    try:
        response = requests.get(f"{BASE_URL}/api/chat/{chat_id}")
        response.raise_for_status()

        data = response.json()
        print("✅ Chat history retrieved")
        print(f"   Chat ID: {data['chat_id']}")
        print(f"   Message count: {data['message_count']}")

        for i, message in enumerate(data["messages"]):
            print(f"   Message {i+1}:")
            print(f"     Q: {message['question']}")
            print(f"     A: {message['answer'][:100]}...")
            print(f"     Time: {message['timestamp']}")

        assert data["chat_id"] == chat_id
        assert "messages" in data
        return data

    except Exception as e:
        print(f"❌ Get chat history failed: {e}")
        return None


def test_get_all_chats():
    print("\n💬 Testing Get All Chats...")

    try:
        response = requests.get(f"{BASE_URL}/api/chat")
        response.raise_for_status()

        data = response.json()
        print("✅ All chats retrieved")
        print(f"   Total sessions: {data['total_sessions']}")
        print(f"   Total messages: {data['total_messages']}")

        for chat in data["chats"]:
            print(f"   Chat {chat['chat_id'][:8]}...")
            print(f"     Messages: {chat['message_count']}")
            if chat["first_question"]:
                print(f"     First Q: {chat['first_question'][:50]}...")
            print(f"     Last active: {chat['last_message_time']}")

        assert "chats" in data
        assert "total_sessions" in data
        return data

    except Exception as e:
        print(f"❌ Get all chats failed: {e}")
        return None


def test_chat_with_multiple_messages(chat_id):
    print("\n💬 Testing Multiple Messages in Same Chat...")

    questions = [
        "What evaluation metrics are used for text-to-SQL systems in the research papers?",
        "What are the main challenges in text-to-SQL conversion mentioned in the documents?",
        "Which large language models are compared in the text-to-SQL evaluation studies?",
    ]

    responses = []

    for i, question in enumerate(questions):
        try:
            payload = {"question": question, "chat_id": chat_id}

            response = requests.post(
                f"{BASE_URL}/api/chat",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            print(f"✅ Message {i+1} sent: {question}")
            responses.append(data)

        except Exception as e:
            print(f"❌ Message {i+1} failed: {e}")
            return None

    return responses


def test_invalid_chat_history():
    """Test getting history for non-existent chat"""
    print("\n💬 Testing Invalid Chat History...")

    try:
        fake_chat_id = "non-existent-chat-id"
        response = requests.get(f"{BASE_URL}/api/chat/{fake_chat_id}")

        if response.status_code == 404:
            error_data = response.json()
            print(f"✅ Invalid chat ID correctly rejected: {error_data['detail']}")
            return True
        else:
            print("❌ Invalid chat ID was accepted")
            return False

    except Exception as e:
        print(f"❌ Invalid chat history test failed: {e}")
        return False


def main():
    print("🧪 Testing Chat Endpoints")
    print("=" * 50)

    # Test create chat
    chat_id = test_create_chat()
    if not chat_id:
        print("❌ Cannot continue without chat_id")
        return

    # Test sending messages
    first_message = test_send_chat_message(chat_id)
    if not first_message:
        print("❌ Cannot continue without successful message")
        return

    # Test multiple messages
    multiple_messages = test_chat_with_multiple_messages(chat_id)

    # Test getting chat history
    history = test_get_chat_history(chat_id)

    # Test getting all chats
    all_chats = test_get_all_chats()

    # Test invalid scenarios
    invalid_test = test_invalid_chat_history()

    print("\n" + "=" * 50)
    if all(
        [chat_id, first_message, multiple_messages, history, all_chats, invalid_test]
    ):
        print("🎉 All chat tests passed!")
        print(f"💬 Created chat session: {chat_id}")
        print("📝 Sent multiple messages successfully")
        print("📊 Retrieved chat history and summaries")
    else:
        print("❌ Some chat tests failed.")


if __name__ == "__main__":
    main()
