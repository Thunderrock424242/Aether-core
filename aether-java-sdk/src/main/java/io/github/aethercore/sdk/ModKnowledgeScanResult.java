package io.github.aethercore.sdk;

import java.util.List;

/**
 * Result payload for mod-knowledge scans.
 */
public record ModKnowledgeScanResult(List<SubsystemKnowledgeIndex> indexes, boolean fromCache) {
}
