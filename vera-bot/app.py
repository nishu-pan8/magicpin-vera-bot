from fastapi import FastAPI
from context_store import contexts
from composer import compose_message

app = FastAPI()

@app.get("/v1/healthz")
def health():

    return {
        "status": "ok",
        "contexts_loaded": {
            "category": len(contexts["category"]),
            "merchant": len(contexts["merchant"]),
            "customer": len(contexts["customer"]),
            "trigger": len(contexts["trigger"])
        }
    }


@app.get("/v1/metadata")
def metadata():

    return {
        "team_name": "Nishu Panwar",
        "model": "GPT-5.5",
        "approach": "Deterministic merchant-aware composer",
        "version": "1.0"
    }


@app.post("/v1/context")
def context(payload: dict):

    scope = payload["scope"]

    contexts[scope][payload["context_id"]] = payload

    return {
        "accepted": True
    }


@app.post("/v1/tick")
def tick(payload: dict):

    merchant_id = payload["merchant_id"]

    merchant = contexts["merchant"].get(merchant_id)

    category_slug = merchant["payload"]["category_slug"]

    category = contexts["category"].get(category_slug)

    trigger = payload["trigger"]

    result = compose_message(
        category["payload"],
        merchant["payload"],
        trigger
    )

    return {
        "actions": [result]
    }


@app.post("/v1/reply")
def reply(payload: dict):

    return {
        "handled": True
    }