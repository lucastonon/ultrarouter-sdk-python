# Models and key info

## List the catalog

`client.models.list()` (`GET /v1/models`) returns a [`ModelList`](types-reference.md#modellist)
of the models your workspace can use, with pricing and capabilities. Filter by provider or
capability:

```python
from ultrarouter import UltraRouter

client = UltraRouter()
catalog = client.models.list(provider="openai")
for model in catalog.data:
    print(
        model.id,
        model.context_length,
        model.pricing.input_usd_per_1m,
        model.pricing.output_usd_per_1m,
    )

tool_models = client.models.list(capability="tools")
print([m.id for m in tool_models.data])
```

Prices are reported per million tokens, both as integer micro-USD (`input_micro_usd_per_1m`)
and as USD floats (`input_usd_per_1m`).

## One model and its offers

`client.models.retrieve(model_id)` (`GET /v1/models/{id}`) returns a
[`ModelDetail`](types-reference.md#modeldetail) with every provider offer for the model. The
provider-prefixed id (with its `/`) is passed as-is; the SDK encodes it.

```python
detail = client.models.retrieve("openai/gpt-5.2")
print(detail.name, detail.capabilities, detail.weights)
for offer in detail.offers:
    print(offer.provider, offer.pricing.input_usd_per_1m, offer.hosting_jurisdiction)
```

An unknown id raises `NotFoundError`.

## Inspect your API key

`client.key.get()` (`GET /v1/key`) describes the key the client uses: its mode (`live` or
`test`), scopes, limits and spend this period. It is also the simplest way to check
configuration, since a wrong key raises `AuthenticationError`.

```python
info = client.key.get()
print(info.name, info.prefix, info.mode, info.scopes)
print(info.limits.spend_cap_micro_usd, info.usage.key_spent_micro_usd, info.usage.period)
```
