# Source Code Protection for Third-Party Use

When your deployed servers (V6) are used by third parties, you need to be clear **who can see what**, then apply **technical** and **legal** measures.

---

## 1. Who has access to what?

| Scenario | Can they see your source? | What to do |
|---------|---------------------------|------------|
| **Third parties only use the app** (browser/API, no server or image access) | **No.** They only see the running app and API. | Protect **secrets** (env, API keys). No need to ship compiled code for “protection” — they never see the image. |
| **Third parties have the Docker image** (e.g. you give them the image to run on their AWS) | **Yes.** They can extract the filesystem and see whatever is in the image (`.py` and `.so`). | **Harden the image** (see below) + **legal** (license, NDA, restrictions). |
| **Third parties have SSH or shell on your EC2** | **Yes.** They can read files inside the container(s). | Restrict SSH (no third-party access), or give access only to app logs/metrics. Prefer “they use the app, you own the server.” |
| **You host and they only get a URL** (SaaS-style) | **No.** They never get the image or server access. | Best for source protection: keep the image and server under your control; use contracts and terms of use. |

So: **source code protection is only a concern if third parties can get the image or server access.** If they only use the app via URL, focus on secrets and legal terms.

---

## 2. What’s in your image today?

From your current build:

- **Compiled (not human-readable as source):** Most of the backend is built with Cython into `.so` files (e.g. many `*_api.py` → `.so`). The Dockerfile also deletes `.py` under `migrations`, `templates`, and most of `scripts`.
- **Still shipped as `.py` (readable if someone has the image):**
  - **`agents/`** — agent code (e.g. onboarding, signal analyst).
  - **`verticals/`** — vertical-specific logic (e.g. DC2_S).
  - **`mcp_servers/`** — MCP server plugins.
  - **Root-level:** `app_v3_minimal.py`, `config.py`, `extensions.py`, and a few others (needed for imports or config).

So today, **agents, verticals, and mcp_servers are the main areas where source is still visible** to anyone with the image or container filesystem.

---

## 3. What you should do (technical)

### A. Prefer “no image / no server access” (best protection)

- Deploy and run the app **only on your own AWS** (or your controlled infra).
- Give third parties **only**:
  - URL (e.g. `https://www.auctusai.ai/CSPulseV6`), and
  - User accounts / API access as needed.
- They use the app; they never get the image or SSH. **No technical “source hiding” in the image is required for this case** — just keep the image private (e.g. in your ECR, not public).

### B. If third parties will have the image (or server access)

Harden the image so less source is shipped:

1. **Don’t ship secrets**
   - No `.env` or real keys in the image (already in your TODOs). All secrets via env at runtime.

2. **Don’t ship more than you need**
   - Ensure `.dockerignore` excludes `.git`, `*.md` (if not needed at runtime), and any internal docs. No need to strip source from the image if it’s never there.

3. **Compile more Python to .so (optional but strong)**
   - Today `agents/`, `verticals/`, and `mcp_servers/` are **excluded** from Cython and stay as `.py`.
   - To protect that code:
     - In `setup_cython.py`, **remove** `agents`, `verticals`, and `mcp_servers` from `EXCLUDE_DIRS` (or add only the minimal subset that truly must stay as `.py`).
     - Fix any Cython compilation errors (e.g. dynamic imports or unsupported syntax in those dirs).
     - In the Dockerfile, after the Cython step, **delete** the `.py` files in `agents/`, `verticals/`, and `mcp_servers/` (or under specific subdirs) so only `.so` remain.
   - Result: most of your app is in `.so` only; reverse‑engineering is harder (not impossible).

4. **Strip compiled binaries (optional)**
   - After the Cython step, run `strip` on `.so` files to remove symbols. This doesn’t remove the logic but reduces readability of stack traces and symbols.

5. **Keep the image private**
   - Store images in a **private** ECR (or private registry). Only your deployment pipeline and trusted environments pull the image. Don’t publish the image to a public repo if you care about source protection.

6. **Minimize what’s in the image**
   - No debug tools, no `.git`, no test code or docs you don’t need at runtime. Smaller and cleaner also means less to “protect.”

---

## 4. What you should do (legal / contractual)

**Regardless of technical measures**, if third parties use your deployed system (or get a copy of it), you should:

1. **Terms of use / EULA**  
   - Define that they may only use the app as provided; no right to copy, reverse‑engineer, or reuse your code or algorithms.

2. **NDA (if they see anything non-public)**  
   - Require an NDA before giving access to demos, APIs, or any deployment that might expose design or behavior.

3. **License / IP**  
   - State clearly that the software, including any copies or images you provide, is licensed (not sold), and that IP remains yours. Restrict redistribution and sublicensing.

4. **Acceptable use**  
   - Limit use to the agreed purpose (e.g. evaluation, demo, internal use). Prohibit scraping, automated abuse, or use beyond the agreed scope.

5. **Audit / access control**  
   - If they only get a URL, you control who has accounts and what they can do. If they get the image, contractually limit who can use it and where.

Have these reviewed by legal; the exact wording depends on your jurisdiction and business.

---

## 5. Practical checklist for “third parties use my deployed servers”

| Priority | Action |
|----------|--------|
| 1 | **Clarify access:** Do they get only a URL, or the image/server? Prefer URL-only (you host). |
| 2 | **Secrets:** No `.env`/keys in image; all secrets from env/SSM at runtime. |
| 3 | **Image private:** Keep images in private ECR; no public pull. |
| 4 | **Legal:** Terms of use, license, NDA as needed; IP and “no reverse‑engineer” clauses. |
| 5 | **Optional (if they get the image):** Compile `agents/`, `verticals/`, `mcp_servers/` with Cython, remove `.py`, strip `.so`, and minimize contents of the image. |

**Short answer:**  
- If third parties **only use the app** (URL): **source code protection = keep the image and server under your control + protect secrets + legal terms.**  
- If third parties **get the image or server access**: add **image hardening** (compile more to `.so`, remove `.py`, no secrets, private registry) and **strong legal protection** (license, NDA, no reverse‑engineer).
