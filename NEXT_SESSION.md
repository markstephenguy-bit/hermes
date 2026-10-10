# Session Seed — Continuing Hostinger hermes-vps Setup

Paste this whole file as your opening message.

## What happened this session (2026-10-10)

Mark destroyed the old Vultr hermes-vps and rebuilt from scratch on
**Hostinger**, deliberately NOT replicating the old Vultr session's ad-hoc
process (that history had real mistakes: a wrongly-wiped install, vault
incidents, dashboard left unauthenticated). This session followed Nous
Research's *official* install docs (`hermes-agent.nousresearch.com/docs`)
fresh instead, plus genuinely-useful Hostinger platform features (cloud
firewall, Docker Manager understanding) layered on top where they don't
conflict. Full blow-by-blow is in the catalog (tag `hermes`,
`curl "http://192.168.40.2:3003/entities?tags=cs.%7Bhermes%7D&order=created_at.desc&limit=20"`)
— this is just the headline summary.

## Current state — all verified live, not assumed

- **VPS**: `srv2051520.hstgr.cloud`, Hostinger KVM 2, Ubuntu 24.04.5 LTS,
  IP `31.220.53.141`, Phoenix DC. SSH as `root` or `hermes` — both Claude
  Code's key (`~/.ssh/hostinger_hermes_vps_ed25519`) and Mark's own key
  (`~/.ssh/id_ed25519`) are authorized on both users. Mark also has an SSH
  config alias: `ssh hermes-vps` (from his laptop) with keepalives set.
- **Firewall, two layers**: Hostinger cloud firewall (`hermes-vps-baseline`,
  active) + VPS `ufw` (active) — both allow TCP/22 and UDP/51820, deny
  everything else. These are independent; a port must be open in **both**
  to work (learned this the hard way debugging the WireGuard handshake).
- **HermesAgent**: installed via the official installer as a dedicated
  non-root `hermes` user (uid 1000), systemd lingering enabled. Full
  `hermes setup` wizard run section-by-section: model, tts, terminal,
  gateway, tools, telemetry, agent — nothing skipped.
  - **Model**: `deepseek/deepseek-v4.1-flash` via Nous Portal, logged in as
    mark.stephen.guy@gmail.com, credits topped up and verified working live.
  - **Terminal backend**: Docker (sandboxed command execution, matches
    Nous's own security guidance). Docker installed via the official Docker
    apt repo. Hermes's own sandbox containers are ephemeral (`--rm` per
    command) — nothing persists in `docker ps`, that's correct behavior,
    not a bug.
  - **Gateway**: real systemd user service (`hermes-gateway.service`),
    enabled + running, survives reboot/logout via lingering.
  - **Telegram**: connected and confirmed polling (bot token + Mark's user
    ID `8772762199` for the allowlist, both in `~/.hermes/.env` on the VPS).
    Mark was about to test it live from his phone when this session ended
    — **check with him whether it actually worked**, don't assume.
- **WireGuard**: native `wg-quick` on the VPS (NOT WireGuard Easy — that
  was tried via Hostinger's Docker Manager catalog first, had a broken
  admin login bug, was torn down). Replaced the dead Vultr peer entry on
  fileserver's `wg0.conf` with the new VPS's key via Salt
  (`scripts/salt_client.py fileserver cmd.run "..."`, needs `VAULT_PASSCODE`
  env var — ask Mark for it live, don't hardcode, don't persist).
  Handshake confirmed, 0% packet loss to fileserver AND w_workstation,
  and the local Qwen endpoint (`192.168.40.100:8090/v1/models`) returns
  HTTP 200 through the tunnel. **Tunnel works; Qwen is NOT yet wired into
  Hermes's own model config** — that's the next real step.
- **Abandoned Hostinger "Hermes Agent" app** (the packaged marketplace
  product, unrelated instance from before this session): app deleted by
  Mark, but the underlying subscription ($21.99/mo) may still be
  auto-renewing — Mark explicitly did NOT want it touched further without
  him looking at the billing page himself. Don't act on it; ask him.

## What's NOT done yet — pick up here

Mark's explicit ask, interrupted by the session limit:
1. **Set Qwen (local, via the WireGuard tunnel) as the MAIN model**, with
   DeepSeek V4.1 Flash as the fallback (`hermes fallback add` — same
   picker as `hermes model`, already scoped out this session, not yet run).
   Qwen's endpoint: `http://192.168.40.100:8090/v1` (OpenAI-compatible,
   ik_llama.cpp). Use "Custom endpoint" in the `hermes model` provider
   picker (was option 41 in the provider list this session — verify it's
   still that number, the list can reorder).
2. **Configure cheap/free Nous Portal models for things Qwen can't do**
   (explicitly: image processing/vision — Qwen's endpoint is text-only
   per earlier catalog notes). Mark said "go cheap in the model selections
   first" — prioritize free tier or lowest-cost options, not premium ones,
   for these auxiliary roles. Look at `hermes model` → option 43
   "Configure auxiliary models..." or the `auxiliary:` block in
   `config.yaml`.
3. Confirm with Mark whether Telegram actually worked for him when he
   tested it on his phone.

## Ground rules reaffirmed/established this session

- **Don't presuppose from past session history** — Mark explicitly
  corrected this mid-session: "current information stored in the group
  could be wrong... dont presappose what needs to be done what we did
  before." Verify live, don't replay old catalog entities as instructions.
- **Visual confirmation for anything touching money/purchases** — see
  `feedback_visual_confirm_for_money_actions.md` in Claude's own memory.
  Don't narrate billing state as fact; point Mark at the actual page.
- **"The Hostinger way" vs "the Hermes way"**: use Hostinger's own platform
  features (cloud firewall, backups, Docker Manager) where they're genuine
  conveniences that don't conflict with the underlying software; don't use
  them where there's no real integration point (e.g. there's no
  Hostinger-catalog way to deploy custom/private code — that's always SSH
  + the software's own official installer).
- Memory and git upkeep are Claude's job — log to the catalog as things
  happen, commit/push.
