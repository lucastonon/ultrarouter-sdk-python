# History imports

Imports bring existing usage data or traces into the ledger without routing traffic through the
gateway: an exported usage report gives the gateway a spend and model picture from day one;
intact traces (with prompts and outputs, under the workspace's consent) can also feed evals.

An import never invents data it was not given: a usage-only export cannot create prompts,
outputs or quality figures. Imports need a key with `outcomes:write`.

## Preview, then commit

`mode="preview"` parses and reports without storing anything:

```python
from ultrarouter import UltraRouter

client = UltraRouter()
records = [
    {"model": "gpt-5.2-mini", "input_tokens": 1200, "output_tokens": 300, "date": "2026-01-10"},
    {"model": "gpt-5.2", "input_tokens": 800, "output_tokens": 500, "date": "2026-01-10"},
]

preview = client.imports.create(format="openai_usage", records=records, mode="preview")
print(preview.status, preview.import_class, preview.record_count)
print(preview.report.unsupported_fields, preview.report.parse_errors)

committed = client.imports.create(format="openai_usage", records=records, mode="commit")
print(committed.id, committed.status, committed.accepted_count, committed.rejected_count)
```

Pass the raw export as JSON Lines text with `jsonl=` instead of `records=`. `call_type_id=` binds
the imported history to a call type; `import_id=` resumes an earlier import.

## Track and cancel

```python
job = client.imports.get(committed.id)
print(job.status)  # preview, running, completed, cancelled or failed

for item in client.imports.list(limit=10).data:
    print(item.id, item.format, item.status)

if job.status == "running":
    client.imports.cancel(job.id)
```

The `format` names the source adapter for your export; the import's `report` lists anything it
could not use (`unsupported_fields`, `parse_errors`, per-reason counts).
