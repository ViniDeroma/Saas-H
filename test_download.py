import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.config import load_config
from backend.telegram_client import TelegramManager

async def test():
    config = load_config()
    print("Loaded config:", config)
    
    manager = TelegramManager()
    try:
        client = await manager.get_client(config)
        authorized = await client.is_user_authorized()
        print("Authorized:", authorized)
        
        source_input = config.get("source_channel")
        source_entity = await manager.get_entity_safe(source_input)
        print("Resolved source channel:", source_entity)
        
        print("Fetching message ID 220...")
        message = await client.get_messages(source_entity, ids=220)
        print("Fetched message details successfully (contains emojis, omitted print)")
        
        if not message:
            print("Message ID 220 not found. Fetching latest media message instead...")
            async for msg in client.iter_messages(source_entity, limit=20):
                if msg.media:
                    message = msg
                    print("Found alternative media message:", msg.id, type(msg.media))
                    break
        
        if message and message.media:
            print(f"Testing download for message ID {message.id}...")
            temp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "temp_media", f"test_media_{message.id}")
            os.makedirs(os.path.dirname(temp_file), exist_ok=True)
            
            def prog(current, total):
                print(f"Download Progress: {current} / {total}")
                
            res = await client.download_media(message, file=temp_file, progress_callback=prog)
            print("Download Result:", res)
            if res and os.path.exists(res):
                print("Downloaded file size:", os.path.getsize(res), "bytes")
                os.remove(res)
        else:
            print("No message with media found to test download!")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
