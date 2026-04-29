package io.github.aethercore.sdk;

/**
 * Progress snapshot for background mod-knowledge scanning in menu/loading screens.
 */
public record ModKnowledgeScanProgress(int totalFiles, int processedFiles, boolean done, boolean cacheHit, String message) {
    public double percentComplete() {
        if (totalFiles <= 0) {
            return done ? 100.0 : 0.0;
        }
        return Math.min(100.0, (processedFiles * 100.0) / totalFiles);
    }
}
