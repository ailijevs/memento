# Repository Guidelines

These notes describe how the repository is laid out, how we collaborate, and what new contributors should know before writing their first line of code.

## Repository Architecture

```
memento/
├─ README.md                 # High-level product introduction and quick start
├─ doc/                      # Living documentation for internal processes
│  └─ repository-guidelines.md
├─ frontend/                 # React + Vite client application
│  ├─ dist/                  # Production bundles (never edit manually)
│  ├─ node_modules/          # Installed dependencies (managed by npm/pnpm)
│  └─ src/
│     ├─ screens/            # Routed pages (HomeScreen, DetailScreen, …)
│     ├─ resumes/            # Sample resume data files
│     └─ types/              # Shared TypeScript definitions
└─ backend/                  # Planned API/service layer (scaffold as we grow)
   ├─ src/                   # Business logic, controllers, use cases
   ├─ tests/                 # Unit/integration specs
   └─ scripts/               # Operational utilities (db migrations, seeds, etc.)
```

### Root assets
- `README.md` gives newcomers the narrative around the product and should always link to relevant onboarding docs.
- `.gitignore`, formatting configs, CI config, and other automation helpers live at the root once introduced.

### Frontend application (`frontend/`)
- Built with React, TypeScript, and the Vite toolchain. Expect standard Node project conventions (`package.json`, lockfile, `.env`, etc.) even if some files are generated during setup.
- `src/screens/` houses feature-level UI; every screen owns its state hooks and composes shared components.
- `src/resumes/` currently stores source data for the prototype experience; as we add persistence this directory can give way to API fixtures.
- `src/types/` centralizes reusable interfaces (`connections.ts`) to keep data contracts discoverable.
- `dist/` contains transpiled output from `npm run build`. Treat it as disposable.
- Recommended scripts (run from `frontend/`):
  - `npm install`: installs dependencies.
  - `npm run dev`: launches the Vite dev server.
  - `npm run build` / `npm run preview`: produces and inspects production bundles.

### Backend services (`backend/`)
- The directory is a placeholder for now, but we expect a Node/TypeScript or Python service with a similar `src/` + `tests/` split.
- Add subdirectories such as `src/api`, `src/domain`, and `scripts/db` as functionality emerges so teammates can locate code easily.
- Provide a `.env.example` and setup script as soon as the service begins to ensure reproducible environments.

### Documentation (`doc/`)
- Use this folder for onboarding docs, ADRs, API contracts, and how-to guides. 
- Keep everything in Markdown with descriptive filenames (`doc/api-contracts.md`, `doc/runbook-alerts.md`) so people can search quickly.
- Update docs simultaneously with code changes; stale docs create rework for reviewers and newcomers.

## Branching & Workflow Model
- Always branch from `main`. Branch names must be descriptive snake_case (`feature_auth_flow`, `bugfix_connection_timeout`).
- Every unit of work—no matter how small—gets its own branch. Avoid mixing unrelated tasks.
- Never push directly to `main`. It remains the only protected default branch.
- Push early and often to your feature branch so others can fetch your progress and help if needed.
- When the feature is complete, open a pull request (PR) back into `main`. Include screenshots, test results, and context for reviewers.
- Rebase or merge the latest `main` into your branch before requesting review so diffs stay clean.

## Code Development & Review Policy
- Each PR requires at least one reviewer who was not involved in writing the code.
- Keep PRs small (ideally 200–300 lines of delta). If a feature grows larger, break it into vertical slices or scaffolding PRs.
- A PR should not not contain more than one feature of code. Every team member needs to make at least 1-2 PR's per week signifying they have completed that weeks issues unless unforseen circumstances occur.
- Tests (unit or integration) must cover new logic when feasible; if skipped, add a note explaining the follow-up.
- Linting and type checks must pass locally before requesting review (`npm run lint`, `npm run typecheck` once those scripts exist).
- Use meaningful commit messages tying work to tickets or user stories.
- Merges happen only through the PR workflow after approvals and status checks succeed; do not use force pushes on reviewed commits unless coordinated with reviewers.

## Onboarding Checklist
1. **Clone & inspect** – `git clone … && cd memento`. Skim `README.md` and this document to understand conventions.
2. **Tooling** – Install Node.js ≥ 18 (LTS) and your preferred package manager (`npm` by default). Configure an editor with ESLint + Prettier formatting support.
3. **Frontend setup** – `cd frontend && npm install`. Copy `.env.example` to `.env` when available, then run `npm run dev` to verify the UI locally.
4. **Branching practice** – Create a feature branch immediately (`git checkout -b docs_update_branching`) and keep pushing to that branch.
5. **Documentation habit** – Add or update docs in `doc/` when you touch an area of the codebase; every change should be discoverable.
6. **PR etiquette** – Provide context, testing notes, and reviewers in every PR. Review others’ work regularly to spread knowledge and catch regressions early.

Following these guidelines keeps the repository predictable, onboarding-friendly, and ready for rapid iteration. Reach out in team chat if anything here needs clarification.

