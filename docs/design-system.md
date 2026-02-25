# Memento Design System

> A living reference for designing Memento's mobile frontend, rooted in Apple's [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines).

---

## Design Philosophy

### The Three Principles (Apple HIG)

Every screen in Memento follows these three principles:

**Clarity** — The interface is easily understood. Text is legible at every size. Icons are precise and clear. Adornments are subtle and appropriate. A focus on functionality motivates the design.

**Deference** — The UI helps people understand and interact with content, but never competes with it. When someone is viewing a profile card, the chrome fades away. The person's name, photo, and headline are the stars — not the buttons around them.

**Depth** — Visual layers and realistic motion convey hierarchy. Transitions between screens feel physical. Cards sit above backgrounds. Buttons respond to touch with feedback. This depth provides vitality and helps people understand the interface without explanation.

### Memento-Specific Intent

Memento is used at **events, in person, standing up, on a phone**. Every design decision serves that context:

- **Speed over completeness** — Users are in a conversation. Every screen must communicate its purpose in under 2 seconds.
- **One action per screen** — Each screen has a single primary action. No decision paralysis.
- **Thumb-friendly** — Primary actions live in the bottom half of the screen, within natural thumb reach.
- **Glanceable** — Profile cards are scannable. Name, headline, photo — that's all someone needs mid-conversation.

---

## App Shell

The app runs inside a **430px max-width container** (iPhone 16 Pro Max), centered on desktop. On a real phone, it fills the screen naturally.

```
┌─────────────────────────────┐
│     safe-area-inset-top     │  ← Notch / Dynamic Island
│                             │
│  ┌───────────────────────┐  │
│  │     16px margins      │  │  ← Content area
│  │                       │  │
│  │                       │  │
│  │                       │  │
│  │  ┌─────────────────┐  │  │
│  │  │  Primary action  │  │  │  ← Bottom of screen (thumb zone)
│  │  └─────────────────┘  │  │
│  └───────────────────────┘  │
│                             │
│   safe-area-inset-bottom    │  ← Home indicator
└─────────────────────────────┘
```

- `viewport-fit: cover` extends the app behind the status bar
- `env(safe-area-inset-*)` padding prevents content from overlapping system UI
- PWA manifest with `display: standalone` removes browser chrome when added to home screen

---

## Typography

We use the **Geist** font family (closest web equivalent to SF Pro). All text follows Apple's built-in text style hierarchy with exact sizes, line heights, and letter-spacing.

| Style | Size | Weight | Line Height | Letter Spacing | Use Case |
|-------|------|--------|-------------|----------------|----------|
| Large Title | 34px | Bold (700) | 41px | 0.37px | Page titles on primary screens |
| Title 1 | 28px | Bold (700) | 34px | 0.36px | Screen headers (e.g., "Welcome back") |
| Title 2 | 22px | Bold (700) | 28px | 0.35px | Section headers within a screen |
| Title 3 | 20px | Semibold (600) | 25px | 0.38px | Card group titles |
| Headline | 17px | Semibold (600) | 22px | -0.41px | Card titles, row labels |
| Body | 17px | Regular (400) | 22px | -0.41px | Main text, button labels |
| Callout | 16px | Regular (400) | 21px | -0.32px | Supporting text near actions |
| Subhead | 15px | Regular (400) | 20px | -0.24px | Secondary descriptions, form labels |
| Footnote | 13px | Regular (400) | 18px | -0.08px | Timestamps, metadata, errors |
| Caption 1 | 12px | Regular (400) | 16px | 0 | Section headers in caps, badges |
| Caption 2 | 11px | Regular (400) | 13px | 0.07px | Fine print |

### Usage Rules

- **One type hierarchy per screen.** Don't mix Title 1 and Large Title on the same screen.
- **Semantic meaning, not decoration.** Choose a style because of what the text *means*, not how big you want it.
- **Never go below 11px.** Anything smaller is unreadable on mobile.
- **Input fields use Body (17px) minimum.** Below 16px, iOS auto-zooms the viewport on focus.

### CSS Classes

All styles are available as utility classes in `globals.css`:

```css
.text-large-title   /* 34px bold */
.text-title1         /* 28px bold */
.text-title2         /* 22px bold */
.text-title3         /* 20px semibold */
.text-headline       /* 17px semibold */
.text-body           /* 17px regular */
.text-callout        /* 16px regular */
.text-subhead        /* 15px regular */
.text-footnote       /* 13px regular */
.text-caption1       /* 12px regular */
.text-caption2       /* 11px regular */
```

---

## Color System

Memento uses a **dark-first** design. The dark theme is not an afterthought — it's the default, matching the smart-glasses hardware aesthetic.

### Semantic Color Tokens

Following Apple's semantic color naming convention, Memento maps its color tokens to intent, not specific values:

| Token | Dark Mode Value | Purpose |
|-------|----------------|---------|
| `--background` | Near-black | Primary screen background |
| `--foreground` | Near-white | Primary text |
| `--card` | Elevated dark | Cards, grouped content |
| `--muted` | Dark gray | Secondary surfaces |
| `--muted-foreground` | Medium gray | Secondary text, placeholders |
| `--primary` | Light/white | Interactive elements, buttons |
| `--primary-foreground` | Dark | Text on primary buttons |
| `--border` | White at 10% | Subtle dividers |
| `--input` | White at 15% | Input field borders |
| `--destructive` | Red | Delete, error, danger |

### Background Hierarchy (Apple HIG Stacks)

Apple defines two "stacks" of layered backgrounds. Memento uses the **grouped** stack for its card-based layout:

```
Level 0: --background     (screen background)
Level 1: --card           (cards, sheets)
Level 2: --muted          (elements within cards)
```

Each level is slightly lighter than the one below it, creating visual depth without borders.

### Rules

- **Never use raw hex/rgb values in components.** Always use the CSS variable tokens.
- **Interactive elements use `--primary`.** This establishes a consistent affordance across the app.
- **Destructive actions use `--destructive`.** Red, always.
- **4.5:1 minimum contrast ratio** between text and its background (WCAG AA).

---

## Spacing & Layout

### The 16px Rule

All screens use **16px (px-4) horizontal margins**. This is Apple's standard side margin for iPhone apps. No exceptions.

### Vertical Rhythm

Spacing between elements follows a consistent scale:

| Spacing | Value | Use Case |
|---------|-------|----------|
| Tight | 4px | Between label and its input |
| Base | 8px | Between items in a list |
| Comfortable | 12px | Between sections within a card |
| Loose | 16px | Between cards |
| Section | 24px | Between major sections |
| Screen | 32px+ | Between screen header and content |

### Touch Targets

**Every interactive element must be at least 44x44pt.** This is non-negotiable.

| Component | Minimum Height | Actual Size |
|-----------|---------------|-------------|
| Buttons | 44px | 50px |
| Input fields | 44px | 50px |
| List rows | 44px | 48-56px |
| Icon buttons | 44px | 44px (with padding) |
| Links in text | 44px tap area | May appear smaller visually, but the tap target extends |

### Border Radius

iOS uses **continuous (squircle) corners**, not circular arcs. Approximate with:

| Element | Border Radius |
|---------|--------------|
| App icon | 22px (on 80px icon) |
| Cards | 16px |
| Buttons | 14px |
| Input fields | 12px |
| Badges/pills | 9999px (full) |
| Avatars | 9999px (full circle) |

---

## Navigation Patterns

### Screen Types

Memento uses three screen patterns:

**1. Full-screen** — Welcome, login, signup, onboarding. No navigation bar. Content fills the viewport. Used for focused, single-purpose flows.

**2. Stack navigation** — Drill-down from a list to a detail view. Has a back button (chevron-left) in the top-left. Used for browsing (event directory → profile detail).

**3. Tab-based** — Primary app structure after onboarding. Maximum 5 tabs. Each tab is its own navigation stack. Used for: Events, Directory, Profile, Settings.

### Transitions

- **Push** (left-to-right): navigating deeper into content
- **Modal** (bottom-to-top): temporary tasks, forms, confirmations
- **Fade**: switching tabs

### Rules

- **Never dead-end.** Every screen must have a way back or forward.
- **No hamburger menus.** Apple recommends tab bars for top-level navigation.
- **Back button goes back.** Don't repurpose it. Don't hide it.
- **Modal for interruptions only.** If it's part of the main flow, push it.

---

## Component Patterns

### Buttons

```
Primary:   Filled, --primary bg, 50px tall, 14px radius, text-body
Secondary: Outlined, --border, 50px tall, 14px radius, text-body
Ghost:     No border, text only, 44px tall, text-body, muted-foreground
```

- One primary button per screen.
- Primary actions use filled buttons. Secondary/cancel use ghost.
- Destructive buttons use filled with `--destructive`.
- Always show a loading spinner when the button triggers an async action.

### Input Fields

- 50px tall, 12px border radius
- 17px (Body) font size — **critical** to prevent iOS zoom
- 16px left padding (or 48px if there's a leading icon)
- Placeholder text in `--muted-foreground`
- Labels above the field, not inside

### Cards

- 16px border radius
- 16px internal padding
- Background: `--card` (one level above `--background`)
- No drop shadows in dark mode — use border or background elevation
- Content follows the standard spacing scale

### Profile Cards (Memento-Specific)

The profile card is the most important component in Memento. It's what someone sees when they look at a person through the glasses and what appears after recognition.

```
┌──────────────────────────────┐
│  ┌────┐                      │
│  │    │  Name (Headline)     │
│  │ 📷 │  Title (Subhead)     │
│  │    │  📍 Location (Cap1)  │
│  └────┘                      │
│──────────────────────────────│
│  Bio text (Subhead, 2-3      │
│  lines max, muted-fg)        │
│──────────────────────────────│
│  EXPERIENCE (Caption1, caps) │
│  Role Title (Subhead, bold)  │
│  Company (Footnote, muted)   │
│──────────────────────────────│
│  EDUCATION (Caption1, caps)  │
│  School (Subhead, bold)      │
│  Degree, Field (Footnote)    │
└──────────────────────────────┘
```

Design intent: **Scan the top. Read the rest if interested.** Photo + name + headline must be parseable in under 1 second.

---

## Onboarding Design (Apple HIG: First Launch)

Apple's guidance for first-launch experiences:

1. **Get to content fast.** Don't show tutorials, splash screens, or terms-of-service walls before the user sees value.
2. **Minimize setup friction.** Ask for the minimum. Derive what you can (e.g., name from Google OAuth metadata).
3. **Progressive disclosure.** Don't explain everything upfront. Teach by doing.
4. **Provide a skip option.** If LinkedIn import isn't possible, let people fill in manually later.
5. **Don't re-onboard returning users.** Check for existing profile and skip straight to the app.

### Memento's Onboarding Flow

```
Welcome → Sign Up / Sign In → LinkedIn Import → Profile Preview → Dashboard
   │              │                  │                  │
   │         (Google OAuth       (paste URL,        (review what
   │          = fastest path)     we do the rest)    others will see)
   │
   └── Returning user: straight to Dashboard
```

Each step is **one screen, one action**:
- Welcome: tap "Get Started"
- Auth: tap "Continue with Google" (or fill email/password)
- LinkedIn: paste URL, tap "Import"
- Preview: review, tap "Continue"

---

## Accessibility

Following Apple HIG accessibility requirements:

- **VoiceOver**: All interactive elements have accessible labels. Images have alt text. Decorative icons are hidden from screen readers.
- **Dynamic Type**: Text scales with system settings. Layouts reflow (don't clip or overflow).
- **Color contrast**: 4.5:1 minimum for normal text, 3:1 for large text (Title 1+).
- **Motion**: Respect `prefers-reduced-motion`. Disable animations when set.
- **Touch targets**: 44x44pt minimum, already enforced by component sizing.

---

## Dark Mode Specifics

Memento defaults to dark mode. Key considerations:

- **No pure black (#000).** Use near-black (`oklch(0.145 0 0)`) for the background. Pure black next to OLED-off pixels creates a harsh edge.
- **No pure white (#fff) text.** Use near-white (`oklch(0.985 0 0)`). Pure white on dark is too high contrast and causes eye strain.
- **Elevation = lightness.** In dark mode, higher elements are lighter (not darker). Cards are lighter than the background. Modals are lighter than cards.
- **Borders at low opacity.** Use `white/10%` for borders instead of gray. This creates a subtle, glassy separation.
- **Avoid colored backgrounds.** Tinted surfaces compete with content. Keep surfaces neutral.

---

## File Reference

| File | Purpose |
|------|---------|
| `frontend/src/app/globals.css` | Theme tokens, HIG typography classes, app shell |
| `frontend/src/app/layout.tsx` | Root layout, app shell wrapper, viewport config |
| `frontend/src/app/manifest.ts` | PWA manifest (standalone mode) |
| `frontend/src/components/ui/` | shadcn primitives (button, input, card, etc.) |
| `docs/design-system.md` | This document |

---

## Quick Reference Card

When building a new screen, check:

- [ ] Max-width 430px (inherited from app shell)
- [ ] 16px horizontal margins (px-4)
- [ ] Typography uses HIG text style classes, not arbitrary sizes
- [ ] All buttons 50px tall, 14px radius
- [ ] All inputs 50px tall, 12px radius, 17px font
- [ ] All interactive elements >= 44x44pt touch target
- [ ] Primary action in the bottom half of the screen
- [ ] One primary action per screen
- [ ] Colors use CSS variable tokens, never raw values
- [ ] Tested at 320px width (iPhone SE) and 430px (iPhone Pro Max)
