# PandaSpool Hub Frontend Architecture & Deployment Guardrails

## 1. Frontend Build Constraints (CRITICAL)
- **NO VITE/REACT**: This project does NOT use Vite, React, or `npm run build` for the frontend, despite any historical artifacts in `web/src`.
- **Vanilla JS Only**: The frontend is a pure Vanilla JS Single Page Application (SPA) driven by hash routing.
- **Master File**: ALL frontend logic changes MUST be made directly to `web/live_app.js`. 
- **Deployment Sync**: After editing `live_app.js`, you MUST copy it to the embedded directory: `cp web/live_app.js web/dist/app.js`.
- **GO EMBED ARCHITECTURE**: The backend uses `//go:embed all:dist` (in `web/embed.go`). This means frontend assets are baked into the binary at compile time! **If you modify ANY frontend file (`live_app.js`, `index.html`), you MUST re-run `go build` to bake them into the new binary. SCPing just the `.js` files to the server will DO NOTHING.**

## 2. Rendering & UI Framework
- **DOM Injection**: Do NOT invent new rendering wrappers (e.g., `shell()`). Always use the established pattern: `$("#page").innerHTML = ...` or `root.innerHTML = ...` inside view functions.
- **CSS Framework**: Strictly use **DaisyUI + Tailwind CSS** utility classes for all UI elements. 
- **Modals & Prompts**: Never use browser native `prompt()` or `confirm()`. Use DaisyUI `<dialog class="modal">` components for data intake and dangerous action confirmations.

## 3. Deployment Workflow (WSL Environment)
- **Use WSL**: All build and deployment commands MUST be executed inside the `PandaSpool-Dev` WSL distribution, leveraging the project's root path `/mnt/c/work/3D模型/printpilot-hub`.
- **Workflow**:
  ```bash
  # Execute inside WSL: wsl -d PandaSpool-Dev -e bash -c 'export PATH=$PATH:/usr/local/go/bin && cd /mnt/c/work/3D模型/printpilot-hub && ...'

  # 1. Build for Linux (Native in WSL)
  GOOS=linux GOARCH=amd64 go build -o printpilot-linux-amd64 ./cmd/pandaspool

  # 2. Stop Remote Service
  ssh -i ~/.ssh/openclaw159.pem -o StrictHostKeyChecking=no root@159.75.227.95 "systemctl stop printpilot"

  # 3. SCP Binary
  scp -i ~/.ssh/openclaw159.pem -o StrictHostKeyChecking=no printpilot-linux-amd64 root@159.75.227.95:/opt/printpilot/printpilot

  # 4. Restart Service
  ssh -i ~/.ssh/openclaw159.pem -o StrictHostKeyChecking=no root@159.75.227.95 "systemctl start printpilot"
  ```
