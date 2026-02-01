import ollama
import os

def get_client():
    # Force the client to look at the IPv4 loopback we just configured
    return ollama.Client(host='http://127.0.0.1:11434')