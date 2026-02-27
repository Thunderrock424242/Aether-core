package io.github.aethercore.sdk;

/**
 * Preferred AI backend routing behavior for game clients.
 */
public enum BackendMode {
    /**
     * Prefer local sidecar runtime when available, otherwise fallback to dedicated server.
     */
    AUTO,
    /**
     * Require local sidecar runtime and surface a setup error if unavailable.
     */
    LOCAL,
    /**
     * Require dedicated server runtime and do not try local sidecar startup.
     */
    REMOTE
}
