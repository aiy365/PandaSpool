
import json
import re

with open(r"C:\Users\user\.gemini\antigravity\brain\0b17df1d-4aef-4f93-b5a4-74a851741c5c\.system_generated\logs\transcript_full.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if "func (s *Server) applyIntegrations()" in line:
            data = json.loads(line)
            if "content" in data and "package server" in data["content"]:
                print("FOUND in content length", len(data["content"]))
                with open("server_candidate.txt", "w", encoding="utf-8") as out:
                    out.write(data["content"])
                break

