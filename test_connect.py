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
        print("Starting connection check...")
        status = await manager.check_connection(config)
        print("Status check result:", status)
        
        print("Attempting to send code...")
        res = await manager.send_code(config)
        print("Result:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
