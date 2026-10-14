# Learned-module placement

The gateway inserts a learned context module as a `user` message immediately after the leading
run of `system` messages. That keeps the stable prefix of the prompt byte-identical (good for
provider prompt caching) and puts the learned block ahead of every volatile turn. With no leading
system message, the block goes first.

Two pure helpers reproduce the rule, so a call you make yourself places the module exactly where a
proxied call would. They need no client and are also exported from `ultrarouter.context`.

```python
from ultrarouter import apply_learned_context, learned_placement_index

messages = [
    {"role": "system", "content": "You are a support agent."},
    {"role": "system", "content": "Answer in English."},
    {"role": "user", "content": "Where is my refund?"},
]

print(learned_placement_index(messages))  # 2

placed = apply_learned_context(messages, "Known fact: refunds take up to 14 days.")
for message in placed:
    print(message["role"], "|", message["content"])
```

- `apply_learned_context` returns a **new** list and never mutates its input.
- With `content=None` or `""` (a holdout arm, or no module), it returns the messages unchanged.
- Messages can be dicts or objects with a `role` attribute.
- Only a `system` role counts toward the prefix; a `developer` message ends it.

| Roles | Index |
| --- | --- |
| `[]` | 0 |
| `["user"]` | 0 |
| `["system", "user"]` | 1 |
| `["system", "system", "user"]` | 2 |
| `["system", "user", "system"]` | 1 |
| `["developer", "system", "user"]` | 0 |

The cross-language test fixtures assert that the Python result matches the TypeScript SDK's for
these and other role sequences. `LearnedSession.apply` from [`use_learned`](preflight.md) uses
these helpers.
