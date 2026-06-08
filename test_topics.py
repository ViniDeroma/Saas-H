import json
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetForumTopicsRequest
from telethon.tl.types import InputPeerChannel

with open("telegram_config.json", 'r') as f:
    config = json.load(f)

client = TelegramClient('erome_session', config['api_id'], config['api_hash'])
client.start(phone=config['phone'])

groups = []
for d in client.iter_dialogs():
    if getattr(d.entity, 'forum', False) or 'HotTelegram' in d.title:
        groups.append(d)

for d in groups:
    print(f"Group: {d.title.encode('ascii', 'ignore').decode()} (Forum: {getattr(d.entity, 'forum', False)})")
    try:
        req = GetForumTopicsRequest(
            channel=d.entity,
            offset_date=0,
            offset_id=0,
            offset_topic=0,
            limit=100,
            q=""
        )
        res = client(req)
        print(f"  -> Found {len(res.topics)} topics!")
        for t in res.topics:
            print(f"     - {getattr(t, 'title', 'No Title').encode('ascii', 'ignore').decode()}")
    except Exception as e:
        print(f"  -> Error getting topics: {type(e).__name__}: {e}")
