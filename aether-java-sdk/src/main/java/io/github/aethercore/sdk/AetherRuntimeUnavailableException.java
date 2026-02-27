package io.github.aethercore.sdk;

import java.io.IOException;

/**
 * Raised when local runtime is required but unavailable.
 */
public final class AetherRuntimeUnavailableException extends IOException {
    public AetherRuntimeUnavailableException(String message) {
        super(message);
    }
}
