---
name: Bug Report
about: Report a defect discovered during verification testing
title: '[BUG] '
labels: bug, verification
assignees: ''
---

## Defect Name

<!-- Short descriptive name for the defect -->

## Severity

- [ ] High (crashes, data loss, security flaws)
- [ ] Medium (functional failure with workaround)
- [ ] Low (UI issues, typos, minor edge cases)

## Steps to Reproduce

1. Step 1
2. Step 2
3. Step 3
4. …

## Expected Behavior

<!-- What should happen -->

## Actual Behavior

<!-- What actually happens -->

## Test Case ID

<!-- Link to the test that exposed this defect, e.g. UT-01, IT-02, MT-01 -->

## Environment

- OS: 
- Python/Node version: 
- Backend/Frontend version: 

## Logs / Screenshots / Evidence

<!-- Paste logs, stack traces, or link screenshots -->

---

### Root Cause Analysis (RCA)

<!-- Complete after fix. Required for High severity; recommended for Medium. -->

- **How was the defect discovered?**
- **Which test exposed the issue?**
- **How was the fix verified?**
- **What regression test prevents recurrence?**
- **Are there other portions of the codebase where this issue may still occur?**
