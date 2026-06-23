def compose_message(category, merchant, trigger, customer=None):

    name = merchant["identity"]["name"]

    trigger_type = trigger.get("kind", "")

    if trigger_type == "research_digest":

        digest = trigger.get("title", "")

        return {
            "message": (
                f"{merchant['identity']['owner_first_name']}, "
                f"new research may help your clinic. "
                f"{digest}. Want me to draft a WhatsApp campaign?"
            ),
            "cta": "Reply YES",
            "send_as": "vera",
            "suppression_key": f"{merchant['merchant_id']}_{trigger_type}",
            "rationale": "Research-based engagement"
        }

    elif trigger_type == "performance_drop":

        ctr = merchant["performance"]["ctr"]

        return {
            "message":
                f"Your profile CTR is {ctr*100:.1f}%. "
                "Adding 5 new photos this week can improve visibility. "
                "Should I create a photo checklist?",
            "cta": "Reply YES",
            "send_as": "vera",
            "suppression_key": f"{merchant['merchant_id']}_{trigger_type}",
            "rationale": "Performance improvement"
        }

    return {
        "message":
            f"{name}, I found an opportunity to improve engagement. Want details?",
        "cta": "Reply YES",
        "send_as": "vera",
        "suppression_key": f"{merchant['merchant_id']}_generic",
        "rationale": "Fallback"
    }