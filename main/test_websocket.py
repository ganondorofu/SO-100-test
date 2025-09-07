#!/usr/bin/env python3
"""
WebSocket接続テストツール
サーバーへの接続をテストする簡易ツール
"""

import asyncio
import websockets
import json
import sys

async def test_connection(url):
    """WebSocket接続をテスト"""
    print(f"🔍 Testing connection to: {url}")
    
    try:
        async with websockets.connect(url) as websocket:
            print("✅ Connection successful!")
            
            # ウェルカムメッセージを待機
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📨 Received: {data.get('type', 'unknown')} - {data.get('message', 'no message')}")
            
            # テストメッセージを送信
            test_msg = {"type": "test", "message": "Hello from test client"}
            await websocket.send(json.dumps(test_msg))
            print("📤 Test message sent")
            
            # 応答を待機
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"📨 Response: {response_data}")
            
    except ConnectionRefusedError:
        print("❌ Connection refused - Server may not be running")
    except OSError as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_websocket.py ws://IP:PORT")
        print("Example: python test_websocket.py ws://192.168.1.100:8765")
        sys.exit(1)
    
    url = sys.argv[1]
    asyncio.run(test_connection(url))

if __name__ == "__main__":
    main()
