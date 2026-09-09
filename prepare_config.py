import json, time

with open("1-50.txt", "r", encoding="utf-8") as f:
    lines = [l.strip() for l in f if l.strip()]

seen = set()
fb_urls = []
for l in lines:
    url = l.rstrip("/")
    if url not in seen and "firebaseio.com" in url:
        seen.add(url)
        fb_urls.append(url)

print(f"Total unique Firebase URLs: {len(fb_urls)}")

firebases = []
for i, url in enumerate(fb_urls, 1):
    fb_id = f"fb_{i}"
    label = url.replace("https://", "").replace("-default-rtdb.firebaseio.com", "")
    firebases.append({"id": fb_id, "url": url, "label": label})

data = {
    "owners": [1029883095],
    "admins": [],
    "banned": [],
    "free_mode": False,
    "approved": [],
    "firebases": firebases,
    "users": {},
    "stats": {"total_sent": 0, "total_failed": 0, "api_usage": {}},
    "premium": {"ref_credits": 3},
    "force_join": {"enabled": False, "channels": []},
    "pricing": {"plans": []},
    "redeem_codes": {},
    "settings": {"ref_credits": 3, "max_owners": 6},
    "sms_history": {},
    "activity_log": [],
    "protected_numbers": {},
    "videos": []
}

with open("blast_data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("blast_data.json created with:")
print(f"  - {len(firebases)} Firebase DBs")
print(f"  - Owner ID: 1029883095")
print("Done.")