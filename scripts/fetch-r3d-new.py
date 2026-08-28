#!/usr/bin/env python3
import os, shutil, sqlite3
src = "/var/lib/printpilot/files/inbox"
dst = "/tmp/r3d-new.jpg"
sha = "91fc1a75e81aa0cd98c47fa7a3fe12a11f7992494dd08c316f467072fa42451d"
shutil.copy2(os.path.join(src, sha), dst)
print("copied", dst, os.path.getsize(dst))
