---
name: no-secrets-no-claims
description: "Never commit a secret or an unsubstantiated claim about a named person"
metadata:
  type: feedback
---

**Rule.** Never commit a secret or an unsubstantiated claim about a named person. "UNVERIFIED" in the text is not a fix.

**Why:** git keeps both forever. A repo that is private today may be shared tomorrow.

**How to apply:** Check 15 scans every staged file for credential shapes. The claim half is judgment: if the record does not back it, it stays out.
