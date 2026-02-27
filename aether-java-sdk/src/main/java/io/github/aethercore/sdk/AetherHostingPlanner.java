package io.github.aethercore.sdk;

import java.util.Objects;

/**
 * Computes host placement based on config + runtime role.
 */
public final class AetherHostingPlanner {
    private AetherHostingPlanner() {
    }

    public static HostingDecision decide(HostingRole role, HostingConfig config) {
        Objects.requireNonNull(role, "role");
        Objects.requireNonNull(config, "config");

        if (!config.hostingEnabled()) {
            return HostingDecision.DO_NOT_HOST;
        }

        if (config.backendMode() == BackendMode.LOCAL) {
            return HostingDecision.HOST_LOCALLY;
        }

        if (config.backendMode() == BackendMode.REMOTE) {
            return HostingDecision.USE_DEDICATED_SERVER;
        }

        if (config.preferDedicatedServer()) {
            if (role == HostingRole.DEDICATED_SERVER) {
                return HostingDecision.HOST_LOCALLY;
            }
            return HostingDecision.USE_DEDICATED_SERVER;
        }

        return HostingDecision.HOST_LOCALLY;
    }
}
