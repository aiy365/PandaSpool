# Contributing to PandaSpool

Thanks for taking an interest in PandaSpool 🐼🛠️ — a self-hosted filament and
enclosure control center for the **Bambu Lab** 3D printing ecosystem.

This project is community-driven. Bugs, ideas, docs, and pull requests are all
welcome.

---

## ⚖️ Important: Legal Reminder

PandaSpool is an **independent, unofficial** open-source project. It is **not**
affiliated with, endorsed by, or sponsored by Bambu Lab. The "Bambu Lab" name
and related trademarks are the property of their respective owners.

When contributing:

- **Do not** commit Bambu Lab proprietary firmware, slicing profiles, copyrighted
  artwork, or any material scraped behind their login wall without verifying
  the license.
- **Do not** commit API tokens, account credentials, or any data that could
  identify a real Bambu / Ezviz / eWeLink account.
- Anything you submit under this repository is understood to be released under
  the same **MIT License** as the rest of the project.

---

## 🧰 Development Setup

Requirements:

- **Go 1.22+** (`go version`)
- **Node 20+** (only if you touch `web/` or `enclosure-sensor/`)
- **Python 3.10+** (only for `scripts/` helpers)
- A Bambu Lab printer on the same LAN, or a mocked test fixture

```bash
git clone https://github.com/aiy365/PandaSpool.git
cd PandaSpool

# Build the backend
go build -o pandaspool ./cmd/pandaspool

# Run unit tests
go test ./...

# (Optional) Live-reload dev mode
./pandaspool --dev
```

---

## 🗂️ Repository Layout (Monorepo)

| Path | Purpose | Language |
| --- | --- | --- |
| `cmd/` | Go backend entry point | Go |
| `desk/` | Desktop companion / tray helper | Go |
| `enclosure-sensor/` | 3D WebGL enclosure dashboard | JS / WebGL |
| `material-lab/` | Filament R&D analytics | Go + Python |
| `web/` | Web UI (consumed by `cmd/`) | JS / TS |
| `scripts/` | Deployment & ops helpers (vendored from language stats) | Python / Shell |
| `docs/` | Architecture, governance, design notes | Markdown |
| `firmware/` | Optional MCU firmware sketches | C / Arduino |
| `internal/` | Shared internal Go packages | Go |

---

## 🌿 Branching & Commit Style

- **Branch off `main`**: `feat/<short-topic>`, `fix/<short-topic>`,
  `docs/<short-topic>`, `chore/<short-topic>`.
- **Commit messages**: short imperative summary, optional body explaining
  *why*. Example:
  ```
  feat(spool): auto-inject short code into Bambu Cloud Note
  ```
- **One concern per PR**. Large refactors should be split.
- Run `go test ./...` and `gofmt -l ./...` before pushing. The CI will block
  on either failing.

---

## 🧪 Tests

- Go packages use standard `testing`. Place `*_test.go` next to the code.
- Hardware-touching code (relay, MQTT) **must** have at least a mocked
  interface test — never assume the relay is wired in CI.
- For UI changes in `enclosure-sensor/` or `web/`, attach a screenshot or
  short clip to the PR.

---

## 🌍 Internationalization

- Primary documentation: **English**.
- Chinese mirror: kept in sync in `README.md` (single file, two sections).
- Code comments: English.
- User-facing strings in `web/`: extract to `web/src/i18n/` before adding a
  new language.

---

## 🐞 Reporting Bugs

Use the [Bug Report](../../issues/new?template=bug_report.md) template.
Include:

1. PandaSpool version (`git rev-parse --short HEAD`)
2. Go version (`go version`)
3. Printer model + firmware version
4. Steps to reproduce
5. Logs from `journalctl -u pandaspool` or terminal output

---

## 💡 Feature Requests

Use the [Feature Request](../../issues/new?template=feature_request.md)
template. Tell us **which pain point** the request addresses — not just the
mechanism. The four canonical pain points are documented in `README.md`:

1. Third-party filament UUID mismatch
2. Spool identity chaos (the "5 white PLAs" problem)
3. Toxic fume / exhaust automation
4. Enclosure monitoring blind spots

If your feature lives outside these, that's fine — but say so explicitly.

---

## 🔐 Security

If you discover a security issue, **please do not open a public issue**.
Email the maintainer privately instead. See [`SECURITY.md`](./SECURITY.md) (if
present) for the contact channel.

---

## 📜 License

By submitting a contribution, you agree that your work will be released under
the **MIT License** that covers this project.
