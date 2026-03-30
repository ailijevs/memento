# SBOM Inspection, Vulnerability Analysis & Project Reflection
**Memento — ECE 49595 SD II | Spring 2026**

---

## SBOM Generation

The SBOM was generated using **cyclonedx-py** (initial snapshot) and **Syft** (CI pipeline) in **CycloneDX 1.6 JSON** format. Vulnerability analysis was performed using **pip-audit** against the PyPI advisory database, and **Grype** is configured to run automatically in the CI pipeline.

- SBOM file: [`docs/SBOM.json`](./SBOM.json)
- CI workflow: [`.github/workflows/sbom.yaml`](../.github/workflows/sbom.yaml)

---

## SBOM Inspection and Analysis

### Number of Dependencies Identified

**159 total components** were identified across the full dependency tree:
- **92 direct dependencies** declared in `backend/requirements.txt`
- **67 transitive dependencies** pulled in by those packages

153 of 159 components (96%) have license information. The 6 without are: `dspy`, `dspy-ai`, `multidict`, `pypdfium2`, `setuptools`, and `tiktoken`.

---

### Unexpected Dependencies

Several dependencies appeared that were not expected given the project's purpose:

| Package | Why Unexpected |
|---|---|
| `dspy-ai` / `dspy` | A research-grade LLM framework (Stanford DSPy). It pulls in `litellm`, `optuna`, `huggingface_hub`, `tokenizers`, `tiktoken`, and `numpy` — a heavy ML stack that suggests this was added experimentally and may not be in active use. |
| `pyiceberg` | Apache Iceberg table format library (big data / data lakehouse tooling). This is surprising for a FastAPI backend that uses Supabase as its only database. |
| `mmh3` | A MurmurHash3 hashing library — only needed by Iceberg. Not expected in this codebase. |
| `huggingface_hub` / `tokenizers` | Pulled in transitively by `dspy-ai`. Hugging Face tooling has no apparent use in the current feature set. |
| `numpy` | Pulled in by `dspy-ai`. Not directly used in any backend code. |
| `pdf2image` / `pdfplumber` / `pytesseract` / `python-docx` | PDF/OCR tooling. These suggest a document-processing capability that is not part of the core Memento feature set and may be leftover from an earlier prototype. |
| `SQLAlchemy` / `alembic` | A full ORM and migration tool stack. Memento uses Supabase's PostgREST client (`supabase-py`) — SQLAlchemy is not used directly but is pulled in transitively by another dependency. |

---

### License Analysis

| License | Count | Notes |
|---|---|---|
| MIT | 82 | Fully permissive — no distribution concerns |
| Apache-2.0 | ~40 (combined) | Permissive — requires attribution and NOTICE file in distributions |
| BSD-3-Clause / BSD-2-Clause | ~26 (combined) | Permissive — minimal requirements |
| PSF-2.0 | 2 | Python Software Foundation license — permissive |
| ISC | 3 | Functionally equivalent to MIT |
| MPL-2.0 | ~4 (combined) | **File-level copyleft** — see note below |
| LGPL v2+ | 1 | **Weak copyleft** — see note below |
| Unknown | 6 | Could not be determined from package metadata |

**Potentially Problematic Licenses:**

- **Mozilla Public License 2.0 (MPL-2.0)** — Used by a small number of dependencies. MPL-2.0 is file-level copyleft: if Memento were to modify an MPL-licensed file and distribute it, those modified files must be released under MPL-2.0. Since Memento does not modify the source of these libraries (they are used as-is via pip), and since Memento is a closed academic/commercial project rather than a distributed binary, this is **not a current concern** but would become relevant if the project were ever distributed as a compiled package.

- **LGPL v2+** — One dependency carries this license. LGPL allows linking without copyleft obligations as long as the library remains dynamically linked (the standard case for pip-installed packages). This is **not a concern for the current deployment model** (server-side Python), but commercial distribution would need legal review.

- **6 Unknown licenses** — `dspy`, `dspy-ai`, `multidict`, `pypdfium2`, `setuptools`, and `tiktoken` could not have their licenses resolved from package metadata. These should be manually verified before any commercial distribution.

---

### Transitive Dependencies

67 transitive dependencies were identified that do not appear in `backend/requirements.txt`. The most notable ones that were previously unknown:

| Transitive Dependency | Pulled In By | Notes |
|---|---|---|
| `litellm` | `dspy-ai` | LLM API abstraction layer — not directly used |
| `huggingface_hub` | `dspy-ai` | Hugging Face model registry client |
| `tokenizers` | `dspy-ai` | Rust-based tokenizer (HuggingFace) |
| `optuna` | `dspy-ai` | Hyperparameter optimization framework |
| `numpy` | `dspy-ai` | Numerical computing |
| `SQLAlchemy` + `alembic` | `dspy-ai` or `pyiceberg` | Full ORM stack |
| `Jinja2` + `MarkupSafe` | `alembic` | Templating engine |
| `aiohttp` + family | `dspy-ai` | Async HTTP client stack |
| `pypdfium2` | `pdfplumber` | PDF rendering engine (Chromium-based PDFium bindings) |
| `lxml` | `cyclonedx-python-lib` / `pyiceberg` | XML parsing library |
| `diskcache` | `dspy-ai` | Disk-based cache using pickle serialization |

The most striking takeaway is that `dspy-ai` alone is responsible for pulling in approximately 30+ transitive dependencies covering ML, async HTTP, ORM, and optimization — a significant hidden cost for what may be an unused or experimental import.

---

## SBOM Vulnerability Analysis

Vulnerability scanning was performed using **pip-audit** against the PyPI advisory database.

**7 vulnerabilities across 6 packages** were identified.

| CVE | Package | Severity | Fix Available |
|---|---|---|---|
| CVE-2026-32597 | `pyjwt@2.11.0` | **High** | Yes — upgrade to 2.12.0 |
| CVE-2026-26007 | `cryptography@46.0.4` | **High** | Yes — upgrade to 46.0.5 |
| CVE-2025-69872 | `diskcache@5.6.3` | **High** | No fix released yet |
| CVE-2026-34073 | `cryptography@46.0.4` | **Medium** | Yes — upgrade to 46.0.6 |
| CVE-2026-25645 | `requests@2.32.5` | **Low** | Yes — upgrade to 2.33.0 |
| CVE-2026-32274 | `black@26.1.0` | **Low** | Yes — upgrade to 26.3.1 |
| CVE-2026-4539 | `pygments@2.19.2` | **Low** | No fix released yet |

---

### Top 3 Most Severe Vulnerabilities

#### 1. CVE-2026-32597 — PyJWT 2.11.0 (High)

**Severity:** High (same vulnerability class as CVE-2025-59420 in Authlib, rated CVSS 7.5)

**Description:** PyJWT fails to validate the `crit` (Critical) Header Parameter defined in RFC 7515. When a JWS token contains a `crit` array listing extensions, PyJWT accepts the token instead of rejecting it, violating the RFC's MUST requirement. This allows security policies encoded in critical headers (MFA enforcement, scope restrictions, token binding) to be silently bypassed.

**Exploitability in Memento:** **Directly relevant.** Memento uses PyJWT for Supabase JWT authentication (in `app/auth/dependencies.py`). An attacker who can forge or manipulate a JWT token with a `crit` header claiming to enforce security policies (e.g., MFA requirements) could bypass those policies since PyJWT would accept the token without validating the critical extension. This is a real threat in a multi-library deployment where the token issuer (Supabase) and verifier (PyJWT) may have different expectations.

**Resolution:** Upgrade `pyjwt` from `2.11.0` to `2.12.0` in `backend/requirements.txt`. The fix adds proper `crit` header validation.

---

#### 2. CVE-2026-26007 — cryptography 46.0.4 (High)

**Severity:** High

**Description:** The `public_key_from_numbers()`, `load_der_public_key()`, and `load_pem_public_key()` functions do not verify that a provided elliptic curve point belongs to the expected prime-order subgroup of the curve. An attacker supplying a small-order subgroup public key during ECDH key exchange can leak bits of the victim's private key. When used in ECDSA, weak public keys allow signature forgery. Only SECT curves are affected.

**Exploitability in Memento:** **Low in current context.** Memento uses the `cryptography` library indirectly (via `supabase-py` and `PyJWT` for RS256/ES256 JWT verification). The attack requires control over public key material supplied to the application. Since Memento validates JWTs issued by Supabase's JWKS endpoint (not arbitrary user-supplied keys), and does not perform ECDH key exchange in application code, exploitation is unlikely in the current deployment. However, if the JWKS endpoint were compromised or if the application were extended to support user-provided cryptographic material, the risk would increase significantly.

**Resolution:** Upgrade `cryptography` to `46.0.5` or newer.

---

#### 3. CVE-2025-69872 — diskcache 5.6.3 (High)

**Severity:** High

**Description:** DiskCache uses Python's `pickle` module for serialization by default. An attacker with write access to the cache directory can place a malicious pickled object in the cache; when the application reads from the cache, arbitrary code is executed in the application's process.

**Exploitability in Memento:** **Low in current context.** `diskcache` is a transitive dependency pulled in by `dspy-ai`, which itself appears to be an experimental or unused import in the codebase. If `dspy-ai` is not actively used in production, `diskcache` is never instantiated and the vulnerability is not reachable. However, since it is present in the dependency tree, it is a latent risk — particularly on any deployment where the application runs with shared filesystem access or in a containerized environment with a mounted volume. There is no fix version available yet.

**Resolution:** Remove `dspy-ai` from `requirements.txt` if it is not in active use. This eliminates `diskcache` and ~30 other transitive dependencies. If `dspy-ai` is needed, monitor for a patched version of `diskcache` and restrict cache directory permissions.

---

## Project Reflection

### What We Learned About the Tech Stack

The SBOM analysis revealed that Memento's actual dependency footprint is substantially larger than the ~92 packages in `requirements.txt` suggest. The 67 additional transitive dependencies — particularly those pulled in by `dspy-ai` and `pyiceberg` — expose the project to vulnerabilities and licensing obligations in libraries the team was not aware of and does not directly control.

The most important finding is that `dspy-ai` acts as a dependency multiplier: it pulls in a full ML stack (Hugging Face, LiteLLM, Optuna, NumPy, SQLAlchemy) that has no apparent role in Memento's core feature set (face recognition + LinkedIn profiles). This likely entered the codebase during experimentation and was never removed.

The three authentication-related vulnerabilities (PyJWT, cryptography ×2) are particularly instructive: security-critical libraries require active version management since vulnerabilities are discovered frequently and fixes are released rapidly. Pinning to a specific version without a process to update it is a risk.

### Dependency Risk Rating: **Medium**

The majority of dependencies are well-maintained, permissively licensed, and have known vulnerability fixes available. The risk is elevated from **Low** to **Medium** primarily because:
- The PyJWT vulnerability is directly relevant to the authentication layer
- Several fix-available vulnerabilities have not yet been applied
- The `dspy-ai` dependency cluster significantly expands the attack surface without providing clear production value

### Actions to Take

| Priority | Action |
|---|---|
| **High** | Upgrade `pyjwt` to `2.12.0` — directly affects the auth layer |
| **High** | Upgrade `cryptography` to `46.0.6` — fixes both CVE-2026-26007 and CVE-2026-34073 |
| **Medium** | Remove `dspy-ai` (and `pyiceberg`) from `requirements.txt` if not actively used — eliminates 30+ transitive deps including the `diskcache` RCE risk |
| **Medium** | Upgrade `requests` to `2.33.0` and `black` to `26.3.1` |
| **Low** | Investigate the 6 packages with unknown licenses before any commercial distribution |
| **Ongoing** | The CI pipeline (Grype + pip-audit) now runs on every push and will flag new CVEs automatically |
