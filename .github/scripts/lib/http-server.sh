#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2025-2026 VDI contributors

HTTP_PID=""

start_http_server() {
  local server_dir=$1
  local port_file=$2

  mkdir -p "$server_dir"
  rm -f "$port_file"

  cat >"$server_dir/server.py" <<'EOF'
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"hello from vdi\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


server = HTTPServer(("127.0.0.1", 0), Handler)
with open(sys.argv[1], "w") as port_file:
    port_file.write(f"{server.server_port}\n")
server.serve_forever()
EOF

  python3 "$server_dir/server.py" "$port_file" \
    >"$server_dir/http.log" 2>&1 &
  HTTP_PID=$!
}

wait_for_http_server() {
  local server_dir=$1
  local port_file=$2

  for _ in $(seq 1 30); do
    if [ -s "$port_file" ]; then
      return 0
    fi
    sleep 0.2
  done

  echo "Error: HTTP server did not become ready."
  cat "$server_dir/http.log"
  return 1
}

stop_http_server() {
  if [ -n "$HTTP_PID" ]; then
    kill "$HTTP_PID" 2>/dev/null || true
    HTTP_PID=""
  fi
}
