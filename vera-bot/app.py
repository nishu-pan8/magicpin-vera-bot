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

    scope = payload.get("scope")
    context_id = payload.get("context_id")

    contexts[scope][context_id] = payload

    return {"accepted": True}


@app.post("/v1/tick")
def tick(payload: dict):

    print("========== TICK RECEIVED ==========")
    print(payload)

    return {
        "actions": [
            {
                "message": "Debug action",
                "cta": "View",
                "send_as": "vera",
                "suppression_key": "debug",
                "rationale": "debug"
            }
        ]
    }

@app.get("/v1/debug")
def debug():
    return contexts

@app.post("/v1/reply")
def reply(payload: dict):

    message = payload.get("message", "").lower()

    # hostile user
    hostile_words = [
        "spam",
        "stop",
        "useless",
        "don't message",
        "do not message"
    ]

    if any(word in message for word in hostile_words):
        return {
            "action": "end"
        }

    # auto reply detection
    auto_reply_words = [
        "thank you for contacting",
        "respond shortly",
        "auto reply",
        "automated"
    ]

    if any(word in message for word in auto_reply_words):
        return {
            "action": "wait",
            "wait_seconds": 3600
        }

    # intent / commitment
    if "ok" in message or "lets do it" in message or "what's next" in message:
        return {
            "action": "send",
            "body": "Great. I'll prepare the next step and share the details shortly."
        }

    return {
        "action": "wait",
        "wait_seconds": 1800
    }