#!/bin/bash

echo "☢️ Starting RabidUI Deep Refresh..."

# 1. Refresh Systemd
echo "📡 Reloading systemd daemons..."
sudo systemctl daemon-reload

# 2. Restart Ollama with open networking
echo "🧠 Restarting Ollama service..."
sudo systemctl restart ollama.service

# 3. Force-recreate the RabidUI container
echo "📦 Recycling Docker container..."
sudo systemctl stop rabidui.service
sudo docker rm -f rabidui
sudo systemctl start rabidui.service

# 4. Success check
echo "✅ Refresh Complete!"
echo "📡 Tailing logs (Ctrl+C to exit)..."
sudo journalctl -u rabidui.service -f
