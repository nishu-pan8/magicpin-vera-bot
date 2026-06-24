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
        "model": "claude-3-haiku",
        "approach": "Context-aware LLM composer v2",
        "version": "2.0"
    }


@app.post("/v1/context")
def context(payload: dict):
    scope = payload.get("scope")
    context_id = payload.get("context_id")
    contexts[scope][context_id] = payload
    return {"accepted": True}


@app.post("/v1/tick")
def tick(payload: dict):
    print("========== TICK RECEIVED ==========")

    available_trigger_ids = payload.get("available_triggers", [])

    if not available_trigger_ids:
        return {"actions": []}

    triggers = []

    for tid in available_trigger_ids:
        ctx = contexts["trigger"].get(tid)

        if not ctx:
            continue

        trigger_obj = ctx.get("payload", ctx)
        triggers.append(trigger_obj)

    if not triggers:
        return {"actions": []}

    actions = []

    for trigger in triggers:
        merchant_id = trigger.get("merchant_id")

        if not merchant_id:
            continue

        merchant_ctx = contexts["merchant"].get(merchant_id, {})
        merchant = merchant_ctx.get("payload", merchant_ctx)

        category_slug = merchant.get("category_slug", "")
        category_ctx = contexts["category"].get(category_slug, {})
        category = category_ctx.get("payload", category_ctx)

        try:
            action = compose_message(
                category,
                merchant,
                trigger
            )

            action["trigger_id"] = trigger.get("id", "")
            action["merchant_id"] = merchant_id
            action["customer_id"] = trigger.get("customer_id")
            action["suppression_key"] = trigger.get(
                "suppression_key",
                trigger.get("id", "vera")
            )
            action["send_as"] = "vera"

            actions.append(action)

        except Exception as e:
            print(f"[ERROR] compose_message failed: {e}")

    print(f"[TICK] Returning {len(actions)} actions")

    return {"actions": actions}


@app.get("/v1/debug")
def debug():
    return contexts


@app.post("/v1/reply")
def reply(payload: dict):
    message = payload.get("message", "").lower()

    hostile_words = ["spam", "stop", "useless", "don't message", "do not message"]
    if any(word in message for word in hostile_words):
        return {"action": "end"}

    auto_reply_words = ["thank you for contacting", "respond shortly", "auto reply", "automated"]
    if any(word in message for word in auto_reply_words):
        return {"action": "wait", "wait_seconds": 3600}

    if any(w in message for w in ["ok", "lets do it", "what's next", "yes", "sure", "sounds good"]):
        return {
            "action": "send",
            "body": "Great! I'll get that ready for you and share the details shortly."
        }

    return {"action": "wait", "wait_seconds": 1800}