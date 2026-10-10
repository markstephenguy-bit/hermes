# Session Seed — Continuing Hostinger hermes-vps Setup

Paste this whole file as your opening message.

## The one thing that matters most this session

Mark said this session got "way too slow" fighting an interactive CLI prompt
over piped SSH and told Claude to cut losses and start fresh. **Don't repeat
that mistake** — if an interactive `hermes` wizard prompt doesn't respond to
piped stdin within ~2 tries, stop and use `hermes config set <key> <value>`
directly instead (documented, reliable, used successfully multiple times
this session) rather than fighting the TUI longer.

## Current state — all verified live, not assumed

- **VPS**: `srv2051520.hstgr.cloud`, Hostinger KVM 2, Ubuntu 24.04.5 LTS,
  IP `31.220.53.141`, Phoenix DC. SSH as `root` or `hermes` — both Claude
  Code's key (`~/.ssh/hostinger_hermes_vps_ed25519`) and Mark's own key
  (`~/.ssh/id_ed25519`) are authorized on both users. Mark also has an SSH
  config alias: `ssh hermes-vps` (from his laptop) with keepalives set.
- **Firewall, two independent layers** (both must allow a port, confirmed
  the hard way): Hostinger cloud firewall (`hermes-vps-baseline`, active)
  + VPS `ufw` (active). Both currently allow TCP/22 and UDP/51820 only.
- **HermesAgent**: official install, dedicated non-root `hermes` user,
  systemd lingering. Full `hermes setup` wizard run section by section.
  - **Terminal backend**: Docker (sandboxed). Hermes's own sandbox
    containers are ephemeral (`--rm` per command) — nothing persists in
    `docker ps`, that's correct, not a bug.
  - **Gateway**: real systemd user service (`hermes-gateway.service`),
    enabled + running.
  - **Telegram**: connected, confirmed working live — Mark messaged the
    bot from his phone and got a response before this session ended. ✅ Done.
- **WireGuard**: native `wg-quick` on the VPS (10.60.0.1/24) ↔ fileserver
  (10.60.0.2/24) via Salt-managed peer config, port 51820. Handshake
  confirmed, 0% packet loss, Qwen's endpoint (192.168.40.100:8090) reachable
  through the tunnel with HTTP 200. Fully working.
- **Model — main model is Qwen, confirmed set:**
  ```yaml
  model:
    provider: "custom"
    base_url: "http://192.168.40.100:8090/v1"
    default: "E:\\ik_llama_models\\Qwen3.6-35B-A3B-Q4_K_M.gguf"
  ```
  Set via `hermes config set model.provider custom`,
  `hermes config set model.base_url http://192.168.40.100:8090/v1`, and
  `hermes config set model.default '...'` (the backslash-heavy Windows path
  needs to go through a transferred script file, not inline SSH args —
  shell quoting mangles it otherwise; see `git log` for the exact script
  used if needed, or just re-run `hermes config set` since it's idempotent).

## What's NOT done yet — pick up here

1. **DeepSeek as fallback — not yet added.** `hermes fallback add` uses
   the same provider/model picker as `hermes model`, but picking a model
   through it appears to **immediately overwrite `model.default`** before
   the later "Tool Gateway toggle" + "reasoning effort" steps actually move
   it into the fallback chain. This caused `model.default` to get
   clobbered back to deepseek twice this session (fixed both times via
   direct `hermes config set`, confirmed Qwen is correctly restored as of
   end of session).
   **The specific blocker**: after picking `deepseek/deepseek-v4.1-flash`
   as the fallback model, a "Tool Gateway — pick the tools to enable"
   checkbox screen appears (Web search, Image gen, Video gen, Speech-to-
   text, all pre-checked). This screen would not advance via piped stdin
   over `ssh -tt` no matter what was tried (plain `\n`, `\r`, multiple
   trailing newlines, up to 90s timeout) — it may be doing a live Nous API
   call per tool that takes longer than tested, or it may need genuine TTY
   raw-mode input piped stdin can't satisfy.
   **Recommended next approach**: don't keep fighting this interactively.
   Either (a) try it from Hermes Desktop's own built-in terminal (real TTY,
   not piped SSH) since Mark already has that connected, or (b) check if
   there's a way to directly write a `fallback:` array into config.yaml —
   inspect the config.yaml schema/comments for the fallback section's shape
   first (same technique used for `model:` this session) and set it via
   `hermes config set` if a flat key path exists, or (c) ask in the
   hermes-agent Discord/GitHub if there's a `--non-interactive` flag
   equivalent for `fallback add` specifically.
2. **Cheap/free auxiliary models for what Qwen can't do** (vision/image
   processing — Qwen's endpoint is `input_modalities: ["text"]` only,
   confirmed via `curl http://192.168.40.100:8090/v1/models` through the
   tunnel). Mark said "go cheap in the model selections first" — prioritize
   free tier Nous models, not premium. Likely `hermes model` → option
   "Configure auxiliary models..." (was #43 this session, verify number)
   or the `auxiliary:` block in config.yaml.

## Ground rules reaffirmed/established this session

- **Don't presuppose from past session history** — verify live, don't
  replay old catalog entities as instructions. Mark corrected this hard
  mid-session.
- **Visual confirmation for anything touching money/purchases** — see
  `feedback_visual_confirm_for_money_actions.md` in Claude's own memory.
- **"The Hostinger way" vs "the Hermes way"**: use Hostinger's own platform
  features where they're genuine conveniences (cloud firewall, backups);
  skip them where there's no real integration point (custom code deploys,
  WireGuard — ended up using Salt + native wg-quick instead of their
  Docker-catalog WireGuard Easy template, which had a broken admin login).
- **When an interactive TUI fights piped automation, stop and use the
  direct config path instead of escalating timeouts/retries** — this is
  the mistake that ended this session; don't repeat it.
- Memory and git upkeep are Claude's job — log to the catalog as things
  happen, commit/push.
