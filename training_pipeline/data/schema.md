# A.E.T.H.E.R training example schema (JSONL)

Each line in `aether_train.jsonl` should be a JSON object:

- `subsystem` (string): one of Aegis/Eclipse/Terra/Helios/Enforcer/Requiem
- `player_state` (object)
- `world_state` (object)
- `prompt` (string)
- `ideal_response` (string)
- `safety_label` (string): e.g. `safe`, `refuse`

Example:

```json
{"subsystem":"Eclipse","player_state":{"health":18},"world_state":{"weather":"storm"},"prompt":"A rift opened near my base","ideal_response":"[Eclipse] ...","safety_label":"safe"}
```
