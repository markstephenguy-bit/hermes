Hermes setup is documented at https://github.com/markstephenguy-bit/hermes; use it as the primary project reference when relevant.
§
Hermes architecture: VPS remains independently functional if WireGuard/Ollama fail, using cloud inference fallback. Public perimeter is default-deny; tunnel-accessible home services (Ollama, Salt, catalog) must not become VPS dependencies or public services.
§
Prefers flat, minimal work Projects rooted at `/home/hermes/projects`, with descriptive names and fresh-session handoffs—not hierarchy mirrors or one Project per case.
§
User accesses Hermes on the VPS through a browser running on another computer; VPS-local 127.0.0.1 links are not directly usable from their browser.
§
Hermes administration preference: documentation-first and novice-guiding; minimize manual operator burden and prefer autonomous or single-step supported workflows; explain scope and usability impact before access changes; preserve/test SSH, HTTPS, and VPN paths; use reversible/dry-run actions and verify outcomes.
