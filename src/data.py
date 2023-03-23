import shelve
import os
import atexit

g_dict = None


def init():
    global g_dict
    if g_dict is None:
        filename = os.environ.get("CHAT_DATA_FILE", "__data")
        g_dict = shelve.open(filename, writeback=True)


def close():
    if g_dict is not None:
        g_dict.close()


atexit.register(close)
