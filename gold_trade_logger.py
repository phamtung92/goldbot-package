import json
import os
from datetime import datetime
LOG_FILE = "C:/Users/Administrator/.openclaw/workspace/gold_trade_log.json"
def now_vn():
 return datetime.now().strftime("%Y-%m-%d %H:%M:%S GMT+7")
def load_log():
 if not os.path.exists(LOG_FILE):
  return []
 try:
  with open(LOG_FILE, "r", encoding="utf-8") as f:
   data = json.load(f)
  return data if isinstance(data, list) else []
 except Exception:
  return []
def save_log(entries):
 with open(LOG_FILE, "w", encoding="utf-8") as f:
  json.dump(entries, f, indent=2, ensure_ascii=False)
def append_trade(entry: dict):
 entries = load_log()
 entries.append(entry)
 save_log(entries)
def update_trade(ticket, updates: dict):
 entries = load_log()
 changed = False
 for item in entries:
  if str(item.get("ticket")) == str(ticket):
   item.update(updates)
   changed = True
 if changed:
  save_log(entries)
 return changed
