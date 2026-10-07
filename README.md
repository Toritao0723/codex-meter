# Codex Meter 🦀

A little desktop companion for your agents — starting with **Codex on macOS**.

Built together by Tori + Codex. Remaining account quota, a compact task navigation bar, seven pixel scenes, and one consistent character-landscape style powered by [Tori Patterns](https://patterns.toritao.com/#/photo).

![Seven scenes, one companion](scene-overview.png)

**Latest backup: v1.5.1 / build 11 · 2026-10-08 · macOS Apple Silicon.** This is a private archive repository. The current application supports Codex; other agents are a future direction. No public launch or X post has been made.

## Download / restore

- [macOS Apple Silicon app](Codex-Meter-v1.5.1-macOS-arm64.zip) — the installed app snapshot.
- [Complete source, app and artwork backup](Codex-Meter-v1.5.1-complete-backup.zip) — original folder structure, build scripts, tests, source credits and all previews.
- [Git history bundle](Codex-Meter-v1.5.1-backup.bundle) — all local commits, branches and the `v1.5.1` / `v1.5.1-backup1` tags; source commit `08026b48e00b01ff00cf7722c748975c9119a7f8`.
- [Version manifest](v1.5.1-manifest.json) · [SHA-256 checksums](SHA256SUMS-v1.5.1.txt) · [Full usage notes](SOURCE-README-v1.5.1.md).

The GitHub archive commit and the source commit inside the bundle are separate histories. Use the source ZIP or bundle to build the app, rather than the root archive repository.

### Existing Mac installation

Quit Codex Meter, unzip the app archive, and place `Codex Meter.app` in `~/Applications/`. Open it after signing in to the official Codex app on that Mac. macOS 13+, Apple Silicon and Apple Command Line Tools / Python 3 are required. The app uses local ad-hoc signing and is not Apple-notarized; new machines may need to build it locally. Intel is not verified.

### Build from source

Unzip the complete backup and enter `Codex-Meter-v1.5.1`. Install Apple Command Line Tools if needed, then run:

```sh
xcode-select --install  # only if Command Line Tools are not already installed
python3 -m unittest -v test_bridge.py
./build.sh
mkdir -p "$HOME/Applications"
ditto --norsrc --noextattr "/private/tmp/codex-meter-build/Codex Meter.app" "$HOME/Applications/Codex Meter.app"
open "$HOME/Applications/Codex Meter.app"
```

JavaScript checks, if Node.js is installed: `node --test test_task_nav.cjs test_pet.cjs`.

Restore the Git repository using:

```sh
git clone Codex-Meter-v1.5.1-backup.bundle codex-meter-source
cd codex-meter-source
git checkout v1.5.1-backup1
```

## Seven matching scenes

| Deep work | Cooking ideas | In the flow |
|---|---|---|
| ![Typing in a forest](scene-typing.png) | ![Cooking in warm hills](scene-cooking.png) | ![Tennis on green slopes](scene-tennis.png) |

| A new perspective | Above the clouds | Take your time |
|---|---|---|
| ![Photography in the dunes](scene-photo.png) | ![Flying through character mountains](scene-flight.png) | ![Waiting at a moonlit lake](scene-music.png) |

[![Celebrate a finished turn](scene-done.png)](scene-done.png)

All eight PNGs are 1280 × 720. They contain artwork only, with no personal task titles or account usage. [Video outline and Chinese / English X post drafts](LAUNCH-DRAFT.md) are ready for the next editing session.

## What it does today

- Reads real Codex account quota windows and reset times; quota percentage is not an API balance or a remaining-token count.
- Shows one selected task at a time, with arrows for navigation and reply-needed prompts.
- Five working activities, music while waiting, confetti when a turn finishes.
- Full, compact and pet-only modes; native macOS glass with light / dark appearance.
- Reads local state and the official read-only quota endpoint. Monitoring and cached scenery do not call a model.

Completion means the current response turn ended, not that the whole project is finished. Permission approval popups cannot all be detected reliably. Only recent, unarchived tasks with local logs on this Mac are covered. Other agents are not integrated yet.

## Credits and earlier backup

Based on [Bon Yeung’s Claude-Meter](https://github.com/bonyuiux/Claude-Meter). Original UI and pixel character © 2026 Bon Yeung; original documentation and attribution remain in [UPSTREAM.md](UPSTREAM.md) and source comments. Character landscapes adapt [Tori Patterns Photo Lab](https://patterns.toritao.com/#/photo), with visual inspiration from [Claude FM](https://www.youtube.com/watch?v=tRsQsTMvPNg). Unofficial, not an OpenAI or Anthropic product.

The [v1.3.0 complete backup](Codex-Meter-v1.3.0-complete-backup.zip), [app](Codex-Meter-v1.3.0-macOS-arm64.zip) and [bundle](Codex-Meter-v1.3.0-backup.bundle) remain available. Backups exclude API keys, login credentials, task logs, usage caches and personal app preferences.
