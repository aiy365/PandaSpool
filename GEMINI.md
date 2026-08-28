
# PrintPilot Hub Frontend Architecture & Deployment Guardrails

## 1. Frontend Build Constraints (CRITICAL)
- **NO VITE/REACT**: This project does NOT use Vite, React, or `npm run build` for the frontend, despite any historical artifacts in `web/src`.
- **Vanilla JS Only**: The frontend is a pure Vanilla JS Single Page Application (SPA) driven by hash routing.
- **Master File**: ALL frontend logic changes MUST be made directly to `C:\work\3D模型\printpilot-hub\live_app.js`. 
- **Deployment Sync**: After editing `live_app.js`, you MUST copy it to the embedded directory: `cp live_app.js web/dist/app.js`.

## 2. Rendering & UI Framework
- **DOM Injection**: Do NOT invent new rendering wrappers (e.g., `shell()`). Always use the established pattern: `$("#page").innerHTML = ...` or `root.innerHTML = ...` inside view functions.
- **CSS Framework**: Strictly use **DaisyUI + Tailwind CSS** utility classes for all UI elements. 
- **Modals & Prompts**: Never use browser native `prompt()` or `confirm()`. Use DaisyUI `<dialog class="modal">` components for data intake and dangerous action confirmations.

## 3. Deployment Workflow (WSL Environment)
- **Use WSL**: All build and deployment commands MUST be executed inside the `PrintPilot-Dev` WSL distribution, leveraging the project's root path `/mnt/c/work/3D模型/printpilot-hub`.
- **Workflow**:
  ```bash
  # Execute inside WSL: wsl -d PrintPilot-Dev
  cd /mnt/c/work/3D模型/printpilot-hub

  # 1. Build for Linux (Native in WSL)
  GOOS=linux GOARCH=amd64 go build -o printpilot-linux-amd64 ./cmd/printpilot

  # 2. Stop Remote Service
  ssh -i ~/.ssh/openclaw159.pem -o StrictHostKeyChecking=no root@159.75.227.95 "systemctl stop printpilot"

  # 3. SCP Binary
  scp -i ~/.ssh/openclaw159.pem -o StrictHostKeyChecking=no printpilot-linux-amd64 root@159.75.227.95:/opt/printpilot/printpilot

  # 4. Restart Service
  ssh -i ~/.ssh/openclaw159.pem -o StrictHostKeyChecking=no root@159.75.227.95 "systemctl start printpilot"
  ```
