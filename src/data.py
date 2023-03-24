import shelve
import os
import atexit

filename = os.environ.get("CHAT_DATA_FILE", "__data")
g_dict = shelve.open(filename, writeback=True)
predefined_keys = ["bots"]
for key in predefined_keys:
    if key not in g_dict:
        g_dict[key] = {}

atexit.register(g_dict.close)
