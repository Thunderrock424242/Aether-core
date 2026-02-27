package io.github.aethercore.sdk;

import java.util.List;

/**
 * Knowledge snapshot for a subsystem, derived from local mod folders and jars.
 */
public record SubsystemKnowledgeIndex(String subsystem, String objective, List<ModKnowledgeEntry> entries) {
}
