import requests

BASE_URL = "http://localhost:8000"


def setup_test_data():
    """Set up test data (files and chats) for reset testing"""
    print("🔧 Setting up test data...")

    try:
        # Create chat and send message
        chat_response = requests.post(f"{BASE_URL}/api/chat/create")
        chat_response.raise_for_status()
        chat_id = chat_response.json()["chat_id"]

        # Send a message to the chat
        message_payload = {"question": "Test question for reset", "chat_id": chat_id}

        message_response = requests.post(
            f"{BASE_URL}/api/chat",
            headers={"Content-Type": "application/json"},
            json=message_payload,
        )
        message_response.raise_for_status()

        print(f"✅ Test data created: Chat ID {chat_id}")
        return chat_id

    except Exception as e:
        print(f"❌ Failed to setup test data: {e}")
        return None


def get_current_status():
    """Get current system status"""
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Failed to get status: {e}")
        return None


def test_reset_all_chats():
    """Test resetting all chats"""
    print("\n🔄 Testing Reset All Chats...")

    try:
        # Get status before reset
        before_status = get_current_status()
        if not before_status:
            return False

        print("   Before reset:")
        print(f"     Chat sessions: {before_status['chat_sessions_count']}")
        print(f"     Total messages: {before_status['chat_history_count']}")
        print(f"     Session ID: {before_status['session_id']}")

        # Reset all chats
        reset_response = requests.post(f"{BASE_URL}/api/reset")
        reset_response.raise_for_status()

        reset_data = reset_response.json()
        print(f"✅ Reset response: {reset_data['message']}")

        # Get status after reset
        after_status = get_current_status()
        if not after_status:
            return False

        print("   After reset:")
        print(f"     Chat sessions: {after_status['chat_sessions_count']}")
        print(f"     Total messages: {after_status['chat_history_count']}")
        print(f"     Session ID: {after_status['session_id']}")

        assert after_status["chat_sessions_count"] == 0
        assert after_status["chat_history_count"] == 0
        assert after_status["has_memory"] is False
        assert after_status["session_id"] != before_status["session_id"]

        return True

    except Exception as e:
        print(f"❌ Reset all chats failed: {e}")
        return False


def test_reset_specific_chat():
    print("\n🔄 Testing Reset Specific Chat...")

    try:
        # Create two chats with messages
        chat1_response = requests.post(f"{BASE_URL}/api/chat/create")
        chat1_id = chat1_response.json()["chat_id"]

        chat2_response = requests.post(f"{BASE_URL}/api/chat/create")
        chat2_id = chat2_response.json()["chat_id"]

        # Send messages to both chats
        for i, chat_id in enumerate([chat1_id, chat2_id]):
            message_payload = {
                "question": f"Test message {i+1} for chat {chat_id[:8]}",
                "chat_id": chat_id,
            }

            requests.post(
                f"{BASE_URL}/api/chat",
                headers={"Content-Type": "application/json"},
                json=message_payload,
            )

        print(f"   Created chats: {chat1_id[:8]}... and {chat2_id[:8]}...")

        # Get status before reset
        before_status = get_current_status()
        print(f"   Total sessions before: {before_status['chat_sessions_count']}")

        # Reset specific chat
        reset_payload = {"chat_id": chat1_id}

        reset_response = requests.post(
            f"{BASE_URL}/api/reset",
            headers={"Content-Type": "application/json"},
            json=reset_payload,
        )
        reset_response.raise_for_status()

        reset_data = reset_response.json()
        print(f"✅ Specific reset response: {reset_data['message']}")

        # Verify specific chat was reset
        try:
            chat1_history = requests.get(f"{BASE_URL}/api/chat/{chat1_id}")
            if chat1_history.status_code == 404:
                print("✅ Chat 1 successfully deleted")
            else:
                print("❌ Chat 1 should have been deleted")
                return False
        except Exception:
            print("✅ Chat 1 successfully deleted")

        # Verify other chat still exists
        chat2_history = requests.get(f"{BASE_URL}/api/chat/{chat2_id}")
        if chat2_history.status_code == 200:
            print("✅ Chat 2 still exists")
        else:
            print("❌ Chat 2 should still exist")
            return False

        # Get status after reset
        after_status = get_current_status()
        print(f"   Total sessions after: {after_status['chat_sessions_count']}")

        # Session count should be reduced by 1
        assert (
            after_status["chat_sessions_count"]
            == before_status["chat_sessions_count"] - 1
        )

        return True

    except Exception as e:
        print(f"❌ Reset specific chat failed: {e}")
        return False


def test_reset_nonexistent_chat():
    print("\n🔄 Testing Reset Non-existent Chat...")

    try:
        fake_chat_id = "non-existent-chat-id"

        reset_payload = {"chat_id": fake_chat_id}

        reset_response = requests.post(
            f"{BASE_URL}/api/reset",
            headers={"Content-Type": "application/json"},
            json=reset_payload,
        )
        reset_response.raise_for_status()

        reset_data = reset_response.json()
        print(f"✅ Reset response for non-existent chat: {reset_data['message']}")

        # Should succeed (no error for non-existent chat)
        return True

    except Exception as e:
        print(f"❌ Reset non-existent chat failed: {e}")
        return False


def test_reset_session_id_change():
    """Test that session ID changes on full reset"""
    print("\n🔄 Testing Session ID Change...")

    try:
        # Get initial session ID
        initial_status = get_current_status()
        initial_session_id = initial_status["session_id"]
        print(f"   Initial session ID: {initial_session_id}")

        # Do a full reset
        requests.post(f"{BASE_URL}/api/reset")

        # Get new session ID
        new_status = get_current_status()
        new_session_id = new_status["session_id"]
        print(f"   New session ID: {new_session_id}")

        # Verify session ID changed
        assert initial_session_id != new_session_id
        print("✅ Session ID changed after full reset")

        # Now test specific chat reset (should NOT change session ID)
        setup_test_data()  # Create some test data

        before_specific = get_current_status()
        session_before_specific = before_specific["session_id"]

        # Reset specific chat
        requests.post(
            f"{BASE_URL}/api/reset",
            headers={"Content-Type": "application/json"},
            json={"chat_id": "some-fake-id"},
        )

        after_specific = get_current_status()
        session_after_specific = after_specific["session_id"]

        # Session ID should NOT change for specific reset
        assert session_before_specific == session_after_specific
        print("✅ Session ID unchanged after specific chat reset")

        return True

    except Exception as e:
        print(f"❌ Session ID test failed: {e}")
        return False


def main():
    print("🧪 Testing Reset Endpoint")
    print("=" * 50)

    # Setup initial test data
    test_chat_id = setup_test_data()
    if not test_chat_id:
        print("❌ Cannot continue without test data")
        return

    # Test resetting all chats
    reset_all_result = test_reset_all_chats()

    # Test resetting specific chat
    reset_specific_result = test_reset_specific_chat()

    # Test resetting non-existent chat
    reset_nonexistent_result = test_reset_nonexistent_chat()

    # Test session ID behavior
    session_id_result = test_reset_session_id_change()

    print("\n" + "=" * 50)
    if all(
        [
            reset_all_result,
            reset_specific_result,
            reset_nonexistent_result,
            session_id_result,
        ]
    ):
        print("🎉 All reset tests passed!")
        print("🔄 Full reset functionality verified")
        print("🎯 Specific chat reset functionality verified")
        print("🆔 Session ID behavior verified")
    else:
        print("❌ Some reset tests failed.")


if __name__ == "__main__":
    main()
