# MCP System Prompt — How It Works for Your End Users

This doc describes **how your customers (end users) get and use the CS Pulse MCP system prompt** when they connect Claude (or another MCP client) to your CS Pulse MCP server. It covers product behavior and options you can offer commercially.

---

## 1. What the system prompt is

**CS_PULSE_MCP_SYSTEM_PROMPT.md** (or the resource `cspulse://system-prompt`) tells the AI:

- Its role (Revenue Intelligence advisor for CS teams)
- Tenant model (`customer_id` vs `account_id`)
- Scope convention (account vs portfolio vs node_traversal)
- All 20 tools, when to use them, and how to interpret responses

Without it, the model may still call tools but can misuse parameters or mix scopes. With it, behavior is consistent and safe.

---

## 2. Commercial options for end users

### Option A — **MCP resource (recommended)**

The CS Pulse MCP server exposes the system prompt as an **MCP resource**:

- **URI:** `cspulse://system-prompt`
- **Behavior:** When the client calls **Read resource** for this URI, the server returns the full markdown.

**For your end users:**

1. They add your MCP server in Claude (or Cursor, etc.) using your MCP URL (e.g. `https://your-cspulse.com/mcp` or your CloudFront URL).
2. In **Claude Projects** (or equivalent): they add a **custom instruction** such as:  
   *“When using the CS Pulse MCP server, first read the resource `cspulse://system-prompt` and use its contents as your system prompt for all CS Pulse tool use.”*
3. Or their client app can **automatically** read `cspulse://system-prompt` on connect and inject it as the system prompt — no manual copy/paste.

**Benefits:** One source of truth (your server). You can update the prompt and redeploy; clients that re-read the resource get the new version. No “upload” step for the user.

---

### Option B — **In-app “Copy system prompt”**

In the CS Pulse product UI (e.g. **Settings → Integrations → Claude / MCP**):

- Show the **MCP server URL** and a short setup note.
- Provide a button: **“Copy system prompt”** that copies the full markdown to the clipboard.
- Instructions: *“Paste this into your Claude Project’s custom instructions (or Knowledge).”*

**Benefits:** Works with any client that accepts pasted instructions. No dependency on MCP resources. Simple to implement (expose the same text you serve at `cspulse://system-prompt` via an API or static asset and have the button copy it).

---

### Option C — **Hosted doc / download link**

- Host the system prompt at a **stable URL** (e.g. `https://docs.yourproduct.com/mcp-system-prompt` or `https://your-app.com/api/mcp/system-prompt`).
- In the same Integrations UI, link: *“Download system prompt”* or *“Use this URL in Claude Projects if your client supports URLs.”*

**Benefits:** Easy to open in a browser, share, or attach where the client supports “add URL as knowledge.” You can version or customize by tenant later (e.g. different URLs or query params).

---

### Option D — **Pre-configured Claude Project (by you)**

You maintain a **Claude Project** (or equivalent) that already has:

- Your MCP server configured
- The system prompt in custom instructions / Knowledge

You share the project (e.g. “Duplicate this project”) or a one-time link so the customer gets a ready-to-use setup.

**Benefits:** Zero configuration for the customer. Good for high-touch or enterprise. You control the exact prompt and tool-usage instructions.

---

## 3. Recommended flow for product

1. **Ship the MCP resource**  
   Already implemented: `cspulse://system-prompt` returns the full system prompt. Deployed instances need the prompt file available (see “Deployment” below).

2. **In-app Integrations / MCP page**  
   - MCP server URL (and, if needed, auth).
   - Short instructions: “In Claude, add this MCP server, then add this instruction: *Read the resource `cspulse://system-prompt` and use it as your system prompt for CS Pulse.*”
   - Optional: **“Copy system prompt”** button that copies the same text (from your API or from the resource implementation) for users who prefer to paste into custom instructions.

3. **Docs**  
   - Public or customer doc that repeats the same two paths: (A) use the resource, or (B) copy/paste the system prompt. Link to the in-app Integrations page.

4. **Optional**  
   - Hosted URL for the prompt (Option C) and/or a pre-configured project (Option D) for key accounts.

---

## 4. Deployment: making the prompt available to the server

The server loads the prompt from (first match wins):

1. **`CSPULSE_MCP_SYSTEM_PROMPT_PATH`** — path to a file (e.g. in production).
2. **Repo root** — `CS_PULSE_MCP_SYSTEM_PROMPT.md` when running from the repo.
3. **Next to the server** — `mcp_server/cs_pulse_mcp_system_prompt.md` (e.g. copy the repo file into the backend image).

For **Docker/production**, either:

- Set `CSPULSE_MCP_SYSTEM_PROMPT_PATH` to a path inside the container where you’ve copied or mounted the file, or  
- Add `cs_pulse_mcp_system_prompt.md` to the backend image (e.g. in `mcp_server/`) so the server finds it without env.

---

## 5. Summary for your end users

| Method | End-user action | Best for |
|--------|------------------|----------|
| **MCP resource** | Add MCP server + instruction to “read `cspulse://system-prompt` and use as system prompt” | Claude Projects, Cursor, any client that supports MCP resources |
| **Copy in app** | Click “Copy system prompt” in CS Pulse, paste into Claude/custom instructions | Users who prefer paste; clients without resource support |
| **Hosted URL** | Open or “add URL” in their client if supported | Docs and power users |
| **Pre-configured project** | Duplicate or open the project you provide | Enterprise / high-touch |

Commercially, **Option A (resource) + Option B (copy in app)** gives you a single source of truth on the server, minimal support burden, and a fallback for every client.
