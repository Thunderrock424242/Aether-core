# Publishing and consuming the Aether Java SDK

This repo now includes a Gradle module (`aether-java-sdk`) that publishes a JVM dependency to GitHub Packages.

## Why is there Java code in this repo?

Because your Minecraft NeoForge mod runs on the JVM, and Gradle dependencies are Java/Kotlin artifacts.

- The Python sidecar (`aether_sidecar`) still hosts the AI runtime.
- The Java SDK is only a thin client so the mod can call the sidecar from JVM code.
- If you do **not** want to use the SDK, you can call the sidecar HTTP endpoints directly from your mod and skip this dependency entirely.

## Publish command (local or CI)

```bash
export GITHUB_ACTOR="<your-github-username>"
export GITHUB_TOKEN="<a token with read:packages + write:packages>"
export GITHUB_REPOSITORY="<owner>/<repo>"
gradle :aether-java-sdk:publish
```

Or trigger the GitHub Action **Publish Aether Java SDK** by pushing a tag like:

```bash
git tag java-sdk-v0.1.0
git push origin java-sdk-v0.1.0
```

## NeoForge / Gradle mod usage

In your Minecraft mod `build.gradle`:

```gradle
repositories {
    maven {
        url = uri("https://maven.pkg.github.com/<owner>/<repo>")
        credentials {
            username = project.findProperty("gpr.user") ?: System.getenv("GITHUB_ACTOR")
            password = project.findProperty("gpr.key") ?: System.getenv("GITHUB_TOKEN")
        }
    }
}

dependencies {
    implementation "io.github.aether-core:aether-java-sdk:0.1.0"
}
```

Then in mod code:

```java
AetherClient aether = new AetherClient("http://127.0.0.1:8765");
String response = aether.generate(player.getStringUUID(), "Suggest a build path", "Sentinel");
```

This keeps AI serving in the sidecar while your NeoForge mod hooks into it from the JVM.

## Hosting behavior (auto-host + dedicated server preference)

The SDK now includes a hosting planner so you can model this policy:

- `hostingEnabled=false` -> never host, always connect to configured server URL.
- `hostingEnabled=true` and running on a dedicated server -> host locally on that server.
- `hostingEnabled=true` and running on a client with `preferDedicatedServer=true` -> connect to dedicated server host.
- `hostingEnabled=true` and `preferDedicatedServer=false` -> host locally on current node.

Core classes:

- `HostingRole` (`CLIENT` / `DEDICATED_SERVER`)
- `HostingConfig`
- `AetherHostingPlanner` -> computes host placement decision
- `AetherSidecarManager` -> can auto-start sidecar process when local hosting is selected
- `ModKnowledgeScanner` -> scans local mod folders/jars and builds per-subsystem knowledge snapshots

NeoForge wiring idea (you provide role detection in mod code):

```java
HostingRole role = isDedicatedServer ? HostingRole.DEDICATED_SERVER : HostingRole.CLIENT;
HostingConfig config = new HostingConfig(
    true, // hostingEnabled
    true, // autoStartEnabled
    true, // preferDedicatedServer
    "http://127.0.0.1:8765",
    List.of("./scripts/run_sidecar_dev.sh"),
    Path.of(".")
);

AetherSidecarManager manager = new AetherSidecarManager();
String baseUrl = manager.ensureHosting(role, config);
AetherClient client = new AetherClient(baseUrl);
```

## Config option: scan mod folders/jars into subsystem-local knowledge

`HostingConfig` now supports model-local knowledge scanning:

- `modKnowledgeScanEnabled` turns scanning on/off.
- `modKnowledgeScanRoots` is a list of folders to scan (for example, your `mods/` directory).
- `subsystemObjectives` maps subsystem/model name to its objective prompt context.

When enabled, `AetherSidecarManager.ensureHosting(...)` runs a scan and stores per-subsystem results in `lastKnowledgeIndexes()`.

This is designed for flows where each subsystem model should focus on its objective while sharing discovered local mod/jar context.

## Optional: no SDK approach

If you prefer no extra dependency, use Java's built-in `java.net.http.HttpClient` from your mod to call:

- `POST /generate`
- `POST /backend/warmup?subsystem=...`

This repo's Java module is intended as a convenience layer, not a required architecture change.
