
import json
import re

with open(r"C:\Users\user\.gemini\antigravity\brain\0b17df1d-4aef-4f93-b5a4-74a851741c5c\.system_generated\logs\transcript_full.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        if "content" in data and isinstance(data["content"], str):
            content = data["content"]
            if "func (s *Server) applyIntegrations()" in content and "func (s *Server) automate()" in content:
                # Look for a block that looks like the whole file
                if "package server" in content:
                    print("Found a potential backup block! Length:", len(content))
                    with open("server_backup.go", "w", encoding="utf-8") as out:
                        out.write(content)
                    break

