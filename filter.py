import json
from datetime import datetime, timedelta


with open('otps.json', 'r') as file:
    data = json.load(file)


new_data = []
for obj in data:
    if obj['created_at']:
        time = datetime.fromisoformat(obj['created_at'])
        now = datetime.now()
        difference = now - time
        if difference.days <= 30:
            new_data.append(obj)
    else:
        new_data.append(obj)


with open('otps.json', 'w') as file:
    json.dump(new_data, file, indent=4)