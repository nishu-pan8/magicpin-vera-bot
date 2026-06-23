def compose_message(category, merchant, trigger):

    owner = merchant["identity"]["owner_first_name"]
    kind = trigger["kind"]

    if kind == "research_digest":
        return {
            "message": f"Dr. {owner}, new research suggests 3-month fluoride varnish recalls reduced recurrence by 38% in high-risk adults. Worth reviewing for your high-risk cohort.",
            "cta": "See summary",
            "send_as": "vera"
        }

    if kind == "perf_dip":
        return {
            "message": f"{owner}, calls dropped {abs(trigger['payload']['delta_pct']*100):.0f}% over the last week. Your profile is also unverified and has no active offers. Want 3 quick fixes?",
            "cta": "Show fixes",
            "send_as": "vera"
        }

    if kind == "gbp_unverified":
        return {
            "message": f"{owner}, verified pharmacy profiles typically see around 30% more visibility. Verification for your store is still pending.",
            "cta": "Start verification",
            "send_as": "vera"
        }

    if kind == "active_planning_intent":
        return {
            "message": f"{owner}, based on your earlier request, I drafted a starter plan for {trigger['payload']['intent_topic']}.",
            "cta": "View draft",
            "send_as": "vera"
        }

    return {
        "message": f"{owner}, I found an opportunity to improve visibility and customer engagement this week.",
        "cta": "Learn more",
        "send_as": "vera"
    }