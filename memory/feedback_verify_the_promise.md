---
name: verify-the-promise
description: "Done means the promised behavior was exercised and observed; label claims Verified, Code-shipped or Inferred"
metadata:
  type: feedback
---

**Rule.** A feature is done when its actual behavior has been exercised and observed, not when it typechecks, renders or deploys. Label every claim Verified, Code-shipped or Inferred and say which.

**Why:** a passing test proves the test ran. It never proves the right thing was tested.

**How to apply:**
- Verified: you ran the real path and saw the result.
- Code-shipped: the change is merged but nobody has watched it work.
- Inferred: you reasoned it out. Say so.
