# Frontend Roadmap

## Phase 2: Apply UI to Ongoing Pages & Add Transitions

### 1. Apply design system to in-progress pages

Roll out the current design language (glass surfaces, dark backgrounds, typography hierarchy, NetworkField/Aurora visual language) to:

- Onboarding flow
- Dashboard
- Any new screens that get built

Ensure consistency: one hero visual per screen, strict opacity system, no competing effects.

---

### 2. Page-to-page transitions (morph)

The Aurora shouldn’t feel like a widget that disappears — it should **carry into** the next screen.

**Direction:**

- **Zoom into the white dot** — On "Get Started", the view could zoom into the protagonist (white) particle as the transition. The next page appears as if we’ve entered the dot.
- **Particles morph** — Particles could disperse, fade, or reorganize into the layout of the next page (e.g., become a grid, list, or background pattern).
- **Shared canvas** — Optionally keep a low-opacity particle layer on inner pages so the Aurora lingers instead of vanishing.

**Technical notes:**

- Use View Transitions API or Framer Motion for zoom/morph.
- Coordinate with Next.js App Router (`layout.tsx`, `page.tsx`) so transitions run on route change.
- Decide whether the Aurora canvas unmounts or stays mounted (with reduced activity) on inner pages.

---

### 3. Open questions

- What exactly does "zooming into the white dot" reveal? (e.g., signup form, onboarding wizard)
- Should the particle network persist as a faint background on all pages, or only on the welcome screen?
- How long should the zoom transition be? (~600–800ms is a good starting point)
