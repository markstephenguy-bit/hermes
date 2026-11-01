# System Inventory — Full Ground-Truth Map

Built 2026-11-01 because enough things turned out to not match prior docs,
memory, and even the catalog itself that a from-scratch itemization was
needed before trusting any of it again. Every row below is tagged with how
it was confirmed — don't treat an untagged claim as fact.

**Status key:** ✅ live-confirmed today (docker ps / systemctl / process
list) · 🔶 catalog/doc claims it, not independently re-verified today ·
❌ confirmed gone or moved · ❓ genuinely unknown, needs checking

**Known sources of truth, and why none of them alone is reliable:**
- **Catalog** (`http://192.168.40.2:3003`, Postgres+PostgREST on
  `fileserver`) — the repo's designated authoritative host/service
  registry. Itself stale: still lists `server` as running NPM/AdGuard/
  Plex/WordPress/MeshCentral, none of which is true anymore. Doesn't know
  `hermes-vps` exists at all.
- **NetBox** (`http://192.168.40.100:8080`) — synced hourly from Salt via
  `netbox_sync.py`, but only tracks the 5 hosts hardcoded in that script's
  `MINIONS` dict. Missing `w_desktop` and `w_laptop` entirely, and doesn't
  track services at all, only devices.
- **This repo's docs** (ARCHITECTURE.md etc.) — rewritten 2026-11-01 from
  live verification, but everything written before that point had drifted
  from reality repeatedly, sometimes within days.
- **Hindsight memory** — has the richest history but also the most
  conflicting claims across time (several ports/hosts cited differently in
  different entries, not always flagged as superseded).

None of these should be trusted blind going forward — re-verify live.

## Hosts

| Host | IP | Role | Source |
|---|---|---|---|
| `hermes-vps` | 31.220.53.141 | VPS, Hostinger KVM2 — public front door + Hermes Agent | NetBox only; **not in the catalog at all** |
| `server` | 192.168.40.250 | HP ProDesk 600 G5 Mini — reboot problem under investigation, formerly a Docker host, now runs almost nothing | Catalog + NetBox |
| `fileserver` | 192.168.40.2 | Dell, weakest hardware, but now home to most Docker infra | Catalog + NetBox |
| `w_workstation` | 192.168.40.100 | HP Z4 G4, GP-managed Windows 11 Enterprise domain — runs the Qwen model, Hindsight, Vaultwarden, NetBox | Catalog + NetBox |
| `w_desktop` | 192.168.40.154 | Windows 10 Pro — **Salt-alive, otherwise unused**, no Docker installed | Catalog only, **not in NetBox** |
| `w_laptop` | 192.168.40.54 | Windows 10 Pro — Salt-registered but **currently offline/unreachable** | Catalog only, **not in NetBox** |
| `laptop` (this machine) | 192.168.40.61 | HP ZBook 15 G5 — Mark's daily driver | Catalog + NetBox |

## Services by host

### `hermes-vps` (31.220.53.141)
| Service | Port | Status | Notes |
|---|---|---|---|
| Hermes Agent (native) | 9119 (dashboard), gateway via Telegram | ✅ | Moved here 2026-11-01; see ARCHITECTURE.md |
| NPM | 80/81/443 | ✅ | Public front door for `*.markstephenguy.com` |
| Authentik (server/worker/postgresql) | — | ✅ | SSO gate in front of hermes/hindsight/vault/netbox subdomains |
| WordPress + its MariaDB | — | ✅ | The public site |

### `server` (192.168.40.250)
| Service | Port | Status | Notes |
|---|---|---|---|
| Salt minion | — | ✅ | |
| netbox-sync cron | — | ✅ | `/opt/netbox-sync/`, hourly |
| Hermes Agent (old install) | — | ✅ stopped, not uninstalled | |
| AdGuard Home | 53 | ❌ moved | Now on `fileserver` |
| MeshCentral | 8086 | ❌ moved | Now on `fileserver` |
| Nginx Proxy Manager | 80/443/81 | ❌ moved | Now on `hermes-vps` |
| WordPress + MariaDB | 80/3306 | ❌ moved | Now on `hermes-vps` |
| Plex Media Server | 32400 | ❓ | Catalog claims it; zero containers found live. Explicitly "removed from server" per NEXT_SESSION.md alongside Beszel-hub/Homepage — status elsewhere unconfirmed |
| Beszel Hub | 8090 | ❓ | Same — explicitly removed per NEXT_SESSION.md, not found running anywhere else. A `beszel-agent` runs on `fileserver` but that's the agent, not the hub |
| "Homepage" (dashboard app) | — | ❓ | Only mentioned once, in NEXT_SESSION.md, as explicitly removed. Never otherwise documented — unclear if it's meant to be replaced |
| DuckDNS updater | — | ❓ | Not found live anywhere; `markstephenguy.com` DNS is now handled differently (real registrar + NPM), may be fully obsolete |
| Tailscale | — | ❓ | Catalog says it was already dormant/never-joined as of 2026-07-25; current status unknown |
| Portainer | 9443 | ❓ | Catalog describes it as managing both `server` and `w_workstation` Docker — `server` has no Docker now, status unknown |

### `fileserver` (192.168.40.2)
| Service | Port | Status | Notes |
|---|---|---|---|
| Salt master + API | 4505-4506, 8000 | ✅ | |
| WireGuard tunnel endpoint | — (10.60.0.2) | ✅ | |
| Squid | 3128 | ✅ | |
| catalog-api + catalog-db | 3003 | ✅ | Narrowed scope — hosts/services only, secrets retired |
| AdGuard Home | 53 (DNS), 8080 (admin) | ✅ | Migrated from `server`, undocumented until this sweep |
| lan-local-proxy | 80/443 (native nginx, likely host networking) | ✅ | LAN-local mirror of VPS-NPM routing |
| **Guacamole** (guacamole + guacd + guac-db) | 8095 | ✅ | **Undocumented anywhere before this sweep.** Remote-desktop/SSH gateway, up 4+ weeks. Purpose/usage unconfirmed with Mark |
| MeshCentral | 8086 | ✅ | Migrated from `server`, undocumented until this sweep |
| beszel-agent | — | ✅ | Agent only, not the hub |
| Samba DATA share | 445 | 🔶 | Catalog claim, not re-checked this sweep |

### `w_workstation` (192.168.40.100)
| Service | Port | Status | Notes |
|---|---|---|---|
| llama-server (Qwen3.5-9B) | 8090 | ✅ | The model every Hermes instance depends on |
| Hindsight + hindsight-postgres | 8888, **9999** | ✅ | Second port (9999) previously undocumented |
| Vaultwarden | 8098 | ✅ | Backend for `vault.markstephenguy.com`, gated by Authentik on the VPS |
| NetBox (full stack: netbox-1, worker, mcp sidecar, postgres, 2x redis) | 8080 (UI), 8001 (MCP) | ✅ | Previously described as just "the MCP sidecar" — it's a full 5-container stack |
| Win32-OpenSSH | 22 | 🔶 | Catalog claim |
| Salt minion | — | ✅ | |
| Portainer Agent | 9001 | 🔶 | Catalog claim, not re-checked |

### `w_desktop` (192.168.40.154) — newly discovered this turn
| Service | Port | Status | Notes |
|---|---|---|---|
| Salt minion | — | ✅ | Confirmed alive via `test.ping` just now |
| Docker | — | ❌ confirmed absent | `docker` command not found |
| Portainer Agent | 9001 | 🔶 | Catalog claim |
| Nothing AI-related | — | ✅ | No llama/hermes/hindsight processes found |

### `w_laptop` (192.168.40.54) — newly discovered this turn
| Service | Port | Status | Notes |
|---|---|---|---|
| Salt minion | — | ❌ offline | Registered in Salt and the catalog, `test.ping` returned "not connected" |

### `laptop` (192.168.40.61, this machine)
| Service | Port | Status | Notes |
|---|---|---|---|
| Samba (SMB) | 445 | 🔶 | Catalog claim |
| TigerVNC (isolated desktop) | 5902 | 🔶 | Catalog claim |
| GNOME Remote Desktop (RDP) | 3390 | 🔶 | Catalog claim |
| WireGuard client | — | ✅ confirmed down | Not running right now; broad `AllowedIPs` flagged as needing narrowing before reuse |
| `hostinger_hermes_vps_ed25519` SSH keypair | — | ✅ | Used for Hermes Desktop's SSH connection to `hermes-vps` |

## Open questions this surfaced, not yet answered

- What is Guacamole on `fileserver` actually used for? It's a real, maintained-looking stack (4+ weeks uptime) that appears in zero docs or memory before today.
- Are Plex, the Beszel monitoring hub, DuckDNS, Tailscale, and Portainer genuinely retired, or did they move somewhere not yet found? All were on `server`, which now has zero containers.
- Should `w_desktop` and `w_laptop` be added to `netbox_sync.py`'s `MINIONS` dict so NetBox (and therefore this kind of audit) actually covers them?
- `w_laptop` is offline — worth knowing if that's expected (device is just off/away) or a problem.
- None of catalog, NetBox, or this repo's docs can currently be trusted as a standing source of truth without re-verification — worth deciding whether that's acceptable going forward or whether one of them should be made authoritative and actually kept current.
