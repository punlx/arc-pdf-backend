import asyncio
import json

import websockets

BASE_URL = "localhost:8000"
WS_URL = f"ws://{BASE_URL}/api/ws/chat"


async def test_websocket_basic_chat():
    print("🔌 Testing Basic WebSocket Chat...")

    try:
        async with websockets.connect(WS_URL) as websocket:
            # Send a question
            question_data = {
                "question": "What are the key contributions of the text-to-SQL research papers?"
            }

            await websocket.send(json.dumps(question_data))
            print(f"📤 Sent: {question_data['question']}")

            # Collect all responses
            responses = []
            complete_response = None

            async for message in websocket:
                try:
                    data = json.loads(message)
                    responses.append(data)

                    if data.get("type") == "typing":
                        print(f"⌨️ {data['message']}")
                    elif data.get("type") == "chunk":
                        print(f"📝 Chunk: {data['content']}", end="", flush=True)
                    elif data.get("type") == "complete":
                        print("\n✅ Complete response received")
                        print(f"   Answer: {data['answer'][:100]}...")
                        print(f"   Source: {data['source']}")
                        print(f"   Chat ID: {data['chat_id']}")
                        complete_response = data
                        break
                    elif data.get("type") == "error":
                        print(f"❌ Error: {data['message']}")
                        return False

                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON received: {message}")
                    return False

            # Verify we got a complete response
            assert complete_response is not None
            assert "answer" in complete_response
            assert "chat_id" in complete_response

            return True

    except Exception as e:
        print(f"❌ Basic WebSocket test failed: {e}")
        return False


async def test_websocket_with_chat_id():
    """Test WebSocket with specific chat ID"""
    print("\n🔌 Testing WebSocket with Chat ID...")

    try:
        # First create a chat via REST API
        import requests

        chat_response = requests.post(f"http://{BASE_URL}/api/chat/create")
        chat_id = chat_response.json()["chat_id"]
        print(f"   Using chat ID: {chat_id}")

        async with websockets.connect(WS_URL) as websocket:
            # Send question with chat_id
            question_data = {
                "question": "Continue our conversation about AI",
                "chat_id": chat_id,
            }

            await websocket.send(json.dumps(question_data))
            print(f"📤 Sent to specific chat: {question_data['question']}")

            # Wait for complete response
            async for message in websocket:
                data = json.loads(message)

                if data.get("type") == "complete":
                    print(f"✅ Response received for chat {data['chat_id']}")
                    assert data["chat_id"] == chat_id
                    return True
                elif data.get("type") == "error":
                    print(f"❌ Error: {data['message']}")
                    return False

    except Exception as e:
        print(f"❌ WebSocket with chat ID test failed: {e}")
        return False


async def test_websocket_multiple_messages():
    """Test sending multiple messages in same WebSocket connection"""
    print("\n🔌 Testing Multiple Messages...")

    try:
        async with websockets.connect(WS_URL) as websocket:
            questions = [
                "What is machine learning?",
                "How do neural networks work?",
                "What are the applications of AI?",
            ]

            responses = []

            for question in questions:
                question_data = {"question": question}
                await websocket.send(json.dumps(question_data))
                print(f"📤 Sent: {question}")

                # Wait for complete response
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)

                    if data.get("type") == "complete":
                        print(f"✅ Response {len(responses)+1} received")
                        responses.append(data)
                        break
                    elif data.get("type") == "error":
                        print(f"❌ Error: {data['message']}")
                        return False

                # Small delay between messages
                await asyncio.sleep(1)

            print(
                f"✅ Sent {len(questions)} messages, received {len(responses)} responses"
            )
            assert len(responses) == len(questions)

            return True

    except Exception as e:
        print(f"❌ Multiple messages test failed: {e}")
        return False


async def test_websocket_invalid_json():
    """Test WebSocket with invalid JSON"""
    print("\n🔌 Testing Invalid JSON...")

    try:
        async with websockets.connect(WS_URL) as websocket:
            # Send invalid JSON
            await websocket.send("invalid json {")
            print("📤 Sent invalid JSON")

            # Should receive error response
            message = await websocket.recv()
            data = json.loads(message)

            if data.get("type") == "error" and "JSON" in data.get("message", ""):
                print(f"✅ Invalid JSON correctly rejected: {data['message']}")
                return True
            else:
                print(f"❌ Expected JSON error, got: {data}")
                return False

    except Exception as e:
        print(f"❌ Invalid JSON test failed: {e}")
        return False


async def test_websocket_empty_question():
    """Test WebSocket with empty question"""
    print("\n🔌 Testing Empty Question...")

    try:
        async with websockets.connect(WS_URL) as websocket:
            # Send empty question
            question_data = {"question": ""}
            await websocket.send(json.dumps(question_data))
            print("📤 Sent empty question")

            # Should receive error response
            message = await websocket.recv()
            data = json.loads(message)

            if (
                data.get("type") == "error"
                and "empty" in data.get("message", "").lower()
            ):
                print(f"✅ Empty question correctly rejected: {data['message']}")
                return True
            else:
                print(f"❌ Expected empty question error, got: {data}")
                return False

    except Exception as e:
        print(f"❌ Empty question test failed: {e}")
        return False


async def test_websocket_streaming_chunks():
    """Test that responses come as streaming chunks"""
    print("\n🔌 Testing Streaming Chunks...")

    try:
        async with websockets.connect(WS_URL) as websocket:
            question_data = {
                "question": "Can you provide a detailed analysis of the evaluation methodologies "
                "used in the text-to-SQL research?"
            }

            await websocket.send(json.dumps(question_data))
            print("📤 Sent request for detailed response")

            chunk_count = 0
            typing_received = False
            complete_received = False

            async for message in websocket:
                data = json.loads(message)

                if data.get("type") == "typing":
                    typing_received = True
                    print("⌨️ Typing indicator received")
                elif data.get("type") == "chunk":
                    chunk_count += 1
                    print(f"📝 Chunk {chunk_count}: {data['content'][:20]}...")
                elif data.get("type") == "complete":
                    complete_received = True
                    print(f"✅ Complete response after {chunk_count} chunks")
                    break
                elif data.get("type") == "error":
                    print(f"❌ Error: {data['message']}")
                    return False

            # Verify streaming behavior
            assert typing_received, "Should receive typing indicator"
            assert chunk_count > 0, "Should receive chunks"
            assert complete_received, "Should receive complete response"

            print(f"✅ Streaming verified: {chunk_count} chunks received")
            return True

    except Exception as e:
        print(f"❌ Streaming chunks test failed: {e}")
        return False


async def test_websocket_connection_stability():
    """Test WebSocket connection stability"""
    print("\n🔌 Testing Connection Stability...")

    try:
        # Test multiple connections in sequence
        for i in range(3):
            async with websockets.connect(WS_URL) as websocket:
                question_data = {"question": f"Test message {i+1}"}
                await websocket.send(json.dumps(question_data))

                # Wait for any response
                message = await websocket.recv()
                data = json.loads(message)

                if data.get("type") == "error":
                    print(f"❌ Connection {i+1} failed: {data['message']}")
                    return False

                print(f"✅ Connection {i+1} successful")

        print("✅ All connections stable")
        return True

    except Exception as e:
        print(f"❌ Connection stability test failed: {e}")
        return False


async def main():
    print("🧪 Testing WebSocket Endpoints")
    print("=" * 50)

    # Run all WebSocket tests
    tests = [
        test_websocket_basic_chat(),
        test_websocket_with_chat_id(),
        test_websocket_multiple_messages(),
        test_websocket_invalid_json(),
        test_websocket_empty_question(),
        test_websocket_streaming_chunks(),
        test_websocket_connection_stability(),
    ]

    results = []
    for test in tests:
        try:
            result = await test
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    if all(results):
        print("🎉 All WebSocket tests passed!")
        print("🔌 WebSocket connection working properly")
        print("📝 Streaming functionality verified")
        print("🛡️ Error handling verified")
    else:
        print("❌ Some WebSocket tests failed.")
        print(f"Results: {sum(results)}/{len(results)} tests passed")


if __name__ == "__main__":
    asyncio.run(main())
