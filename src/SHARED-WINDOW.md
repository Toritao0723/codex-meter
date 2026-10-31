# Shared companion protocol v1

Both repositories carry identical SharedCompanion.swift and ui/provider-switch.js. Keep these files in sync.

Each running meter atomically writes its current display payload to a private user Application Support directory. The snapshot includes provider, PID, random process session ID and heartbeat. Peers must be alive and fresh (< 8 seconds). Only the process holding an exclusive nonblocking flock may display its NSPanel. On normal exit or crash the OS releases the lock; the survivor takes over on its next one-second tick.

The visible window uses one selected provider's complete payload, then applies its own language, size and appearance preferences. Switching is explicit, not a timer that unexpectedly changes the task being read. Refresh and open-task actions are forwarded to the selected meter as short-lived, deduplicated commands; all other commands stay local. UUID task validation remains in the owning meter. No authentication material is exchanged.

Single-provider mode reuses the same identity label with no arrow or inactive second tile. Both-provider mode adds a switch arrow to that label and initially uses compact size. Full and minimized modes still work. Updates are needed in both apps; this protocol cannot hide an older incompatible app's window.
