// Shared local window coordination for Tori's Codex / Claude Meter.
// No credentials or conversation contents are exchanged. Files are user-private.
import Foundation
import Darwin

struct CompanionFrame {
    let ownsWindow: Bool
    let payload: [String: Any]
    let providers: [String]
}

final class SharedCompanion {
    let provider: String
    let directory: URL
    private var lockFD: Int32 = -1
    private(set) var ownsWindow = false
    var selected: String
    var onCommand: (([String: Any]) -> Void)?
    private let processID = ProcessInfo.processInfo.processIdentifier
    private let session = UUID().uuidString
    private var lastCommand = ""

    init(provider: String, directory: URL? = nil) {
        self.provider = provider
        self.selected = provider
        self.directory = directory ?? FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/Tori Meter/companion-v1", isDirectory: true)
        try? FileManager.default.createDirectory(at: self.directory, withIntermediateDirectories: true,
            attributes: [.posixPermissions: 0o700])
        lockFD = Darwin.open(self.directory.appendingPathComponent("window.lock").path, O_CREAT | O_RDWR, 0o600)
        if lockFD >= 0 { ownsWindow = flock(lockFD, LOCK_EX | LOCK_NB) == 0 }
    }

    private func write(_ value: [String: Any], name: String) {
        guard let data = try? JSONSerialization.data(withJSONObject: value) else { return }
        let url = directory.appendingPathComponent(name)
        try? data.write(to: url, options: .atomic)
        try? FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
    }

    private func read(_ name: String) -> [String: Any]? {
        guard let data = try? Data(contentsOf: directory.appendingPathComponent(name)), data.count < 1_000_000,
              let value = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return nil }
        return value
    }

    func tick(_ ownPayload: [String: Any], now: TimeInterval = Date().timeIntervalSince1970) -> CompanionFrame {
        write(["provider": provider, "pid": processID, "session": session, "at": now, "payload": ownPayload], name: provider + ".json")
        if !ownsWindow && lockFD >= 0 { ownsWindow = flock(lockFD, LOCK_EX | LOCK_NB) == 0 }
        // If local coordination is unavailable, retain a usable standalone window.
        if lockFD < 0 { ownsWindow = true }
        var values: [String: [String: Any]] = [provider: ownPayload]
        for peer in ["codex", "claude"] where peer != provider {
            guard let value = read(peer + ".json"), value["provider"] as? String == peer,
                  let at = value["at"] as? Double, now - at >= -1, now - at < 8,
                  let pid = value["pid"] as? Int32, kill(pid, 0) == 0,
                  let payload = value["payload"] as? [String: Any] else { continue }
            values[peer] = payload
        }
        let providers = ["codex", "claude"].filter { values[$0] != nil }
        if values[selected] == nil { selected = provider }
        if let command = read(provider + "-command.json"), let id = command["commandId"] as? String,
           id != lastCommand, let at = command["at"] as? Double, abs(now - at) < 10,
           let body = command["body"] as? [String: Any], ["sync", "openTask"].contains(body["type"] as? String ?? "") {
            lastCommand = id
            onCommand?(body)
        }
        var payload = values[selected] ?? ownPayload
        payload["provider"] = selected
        payload["providers"] = providers
        return CompanionFrame(ownsWindow: ownsWindow, payload: payload, providers: providers)
    }

    func sendCommand(_ body: [String: Any]) {
        guard ["codex", "claude"].contains(selected), selected != provider,
              ["sync", "openTask"].contains(body["type"] as? String ?? "") else { return }
        write(["commandId": UUID().uuidString, "at": Date().timeIntervalSince1970, "body": body], name: selected + "-command.json")
    }

    func stop() {
        if read(provider + ".json")?["session"] as? String == session {
            try? FileManager.default.removeItem(at: directory.appendingPathComponent(provider + ".json"))
        }
        if lockFD >= 0 { flock(lockFD, LOCK_UN); Darwin.close(lockFD); lockFD = -1 }
        ownsWindow = false
    }
    deinit { stop() }
}
