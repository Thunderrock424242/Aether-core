package io.github.aethercore.sdk;

/**
 * Single discovered fact about local mod content for subsystem-specific prompts/routing.
 */
public record ModKnowledgeEntry(String source, String detail) {
}
