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

    # The judge sends a list of trigger ID strings
    available_trigger_ids = payload.get("available_triggers", [])

    if not available_trigger_ids:
        print("[WARN] No triggers in payload")
        return {"actions": []}

    # Look up full trigger objects from stored context
    triggers = []
    for tid in available_trigger_ids:
        ctx = contexts["trigger"].get(tid)
        if ctx:
            # Trigger object is nested under "payload" key when stored via /v1/context
            trigger_obj = ctx.get("payload", ctx)
            triggers.append(trigger_obj)

    if not triggers:
        print("[WARN] None of the trigger IDs found in context store")
        return {"actions": []}

    # Pick highest-urgency trigger
    best_trigger = max(triggers, key=lambda t: t.get("urgency", 0))
    merchant_id = best_trigger.get("merchant_id")

    if not merchant_id:
        print("[WARN] Trigger has no merchant_id")
        return {"actions": []}

    print(f"[TICK] trigger={best_trigger.get('id')} kind={best_trigger.get('kind')} merchant={merchant_id}")

    # Look up merchant and category
    merchant_ctx = contexts["merchant"].get(merchant_id, {})
    merchant = merchant_ctx.get("payload", merchant_ctx)

    category_slug = merchant.get("category_slug", "")
    category_ctx = contexts["category"].get(category_slug, {})
    category = category_ctx.get("payload", category_ctx)

    action = compose_message(category, merchant, best_trigger)

    # Add required fields for the judge scorer
    action["trigger_id"] = best_trigger.get("id", "")
    action["merchant_id"] = merchant_id
    action["suppression_key"] = best_trigger.get("suppression_key", best_trigger.get("id", "vera"))
    action["send_as"] = "vera"

    print(f"[TICK] Composed: {action.get('body', '')[:80]}")
    return {"actions": [action]}


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