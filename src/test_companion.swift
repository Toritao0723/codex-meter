import Foundation
import Darwin

let folder = FileManager.default.temporaryDirectory.appendingPathComponent("meter-test-" + UUID().uuidString)
defer { try? FileManager.default.removeItem(at: folder) }
let codex = SharedCompanion(provider: "codex", directory: folder)
let claude = SharedCompanion(provider: "claude", directory: folder)
let a: [String: Any] = ["windows": [["percentUsed": 25]], "taskNav": ["items": [["id": "codex-task"]]]]
let b: [String: Any] = ["windows": [["percentUsed": 60]], "taskNav": ["items": [["id": "claude-task"]]]]
assert(codex.tick(a).ownsWindow)
assert(!claude.tick(b).ownsWindow)
var frame = codex.tick(a)
assert(frame.providers == ["codex", "claude"])
codex.selected = "claude"
frame = codex.tick(a)
assert(frame.payload["provider"] as? String == "claude")
assert((frame.payload["windows"] as? [[String: Int]])?.first?["percentUsed"] == 60)
var commands = 0
claude.onCommand = { body in assert(body["type"] as? String == "sync"); commands += 1 }
codex.sendCommand(["type":"sync"])
_ = claude.tick(b); _ = claude.tick(b)
assert(commands == 1, "Commands must be delivered once")
let stale = codex.tick(a, now: Date().timeIntervalSince1970 + 10)
assert(stale.providers == ["codex"], "Stale peers must leave no empty slot")
codex.stop()
frame = claude.tick(b)
assert(frame.ownsWindow && frame.providers == ["claude"], "Survivor takes ownership")
claude.stop()
let firstClaude = SharedCompanion(provider: "claude", directory: folder)
let secondCodex = SharedCompanion(provider: "codex", directory: folder)
assert(firstClaude.tick(b).ownsWindow)
assert(!secondCodex.tick(a).ownsWindow)
assert(firstClaude.tick(b).providers.count == 2)
firstClaude.stop()
assert(secondCodex.tick(a).ownsWindow)
secondCodex.stop()
print("PASS: single owner, both launch orders, quota selection, once-only command routing, stale peer cleanup, owner quit handoff")
