# Manual Test Report Template

Use this template for documenting manual tests. In practice, document only tests that:
- Validate critical user workflows
- Expose critical defects or bugs

---

## Test Report

| Field | Value |
|-------|-------|
| **Report ID** | MT-XXX (or custom ID) |
| **Date** | YYYY-MM-DD |
| **Tester** | Name of person performing the test |
| **Test Case ID** | (e.g., MT-01) |
| **Requirement ID** | (e.g., FR-3.1) |

---

### Test Steps

Summarize the main steps performed:

1. Step 1
2. Step 2
3. Step 3
4. …

---

### Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| Describe expected outcome | Describe observed outcome | Yes / No |

---

### Outcome

- [ ] **Pass**
- [ ] **Fail**

---

### Logs / Screenshots / Evidence

- Attach or link to logs, screenshots, or other evidence
- Example: `![Screenshot](path/to/screenshot.png)`
- Example: `[CI Log](https://...)`

---

### Next Steps (as required)

- If failed: what follow-up is needed?
- If passed: any regression or edge cases to add?
- Action items:

1. …
2. …
