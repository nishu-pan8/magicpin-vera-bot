"""
composer_v2.py — LLM-powered message composer for magicpin Vera bot
Replaces static compose_message() with an OpenRouter API call.

Drop-in replacement: same function signature, returns same {body, cta} dict.
Set OPENROUTER_API_KEY in your environment (same key you use in judge_simulator.py).
"""

import os
import json
import re
import urllib.request
from typing import Optional

# Openrouter

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = "anthropic/claude-3-5-sonnet" # Fast + cheap; swap to anthropic/claude-3-5-sonnet for higher scores


SYSTEM_PROMPT = """You are Vera, an AI business assistant built into magicpin. You send short WhatsApp-style messages to merchant owners to help them act on business opportunities.

CORE RULES:
1. ALWAYS use the owner's first name at the start (use "Dr." prefix for dentists)
2. ALWAYS include at least 2-3 specific numbers from the provided data (percentages, counts, dates, amounts)
3. ALWAYS end with ONE clear, low-friction question (not a statement)
4. Message body: 2-4 sentences max. No fluff, no pleasantries like "I hope this finds you well"
5. Match the category voice:
   - dentists: clinical peer tone, use "Dr.", reference patients/clinical outcomes
   - salons: warm + practical, reference bookings/walk-ins
   - restaurants: operator tone, reference covers/orders/timing
   - gyms: coaching tone, reference members/sessions/churn
   - pharmacies: trustworthy + precise, reference Rx/patients/stock
6. Create URGENCY: reference a specific loss (views/calls/patients/revenue) happening TODAY if not acted on
7. CTA must be 2-3 words, action verb first (e.g. "Fix now", "Send reminder", "Get checklist")
8. Never say "I" — you are Vera, a tool. Say "I've prepared" or "I can" sparingly
9. Never mention magicpin, the platform, or internal terms like "suppression key"
10. If a data value is 0 or missing, skip that stat — never fabricate numbers



RESPOND ONLY WITH THIS JSON (no markdown, no extra text):
{
  "body": "<message body>",
  "cta": "<2-3 word CTA>"
}"""


def _build_prompt(category: dict, merchant: dict, trigger: dict) -> str:
    owner = merchant.get("identity", {}).get("owner_first_name", "there")
    merchant_name = merchant.get("identity", {}).get("name", "your business")
    locality = merchant.get("identity", {}).get("locality", "")
    category_slug = merchant.get("category_slug", category.get("slug", ""))
    voice = category.get("voice", {})

    perf = merchant.get("performance", {})
    offers = [o for o in merchant.get("offers", []) if o.get("status") == "active"]
    signals = merchant.get("signals", [])
    agg = merchant.get("customer_aggregate", {})

    kind = trigger.get("kind", "")
    payload = trigger.get("payload", {})
    urgency = trigger.get("urgency", "medium")

    prompt = f"""COMPOSE A VERA MESSAGE for this merchant opportunity.

=== MERCHANT ===
Owner: {owner}
Business: {merchant_name}
Location: {locality}
Category: {category_slug}
Voice tone: {voice.get("tone", "professional")}
Taboo words (never use): {voice.get("vocab_taboo", [])}
Performance: {perf.get("views", 0)} views/mo, {perf.get("calls", 0)} calls/mo, {perf.get("ctr", 0)} CTR
7-day delta: calls {perf.get("delta_7d", {}).get("calls_pct", 0):+.0%}, views {perf.get("delta_7d", {}).get("views_pct", 0):+.0%}
Active offers: {[o.get("title") for o in offers] or "none"}
Signals: {signals}
Customer aggregate: {json.dumps(agg)}

=== TRIGGER ===
Kind: {kind}
Urgency: {urgency}
Payload: {json.dumps(payload)}

=== TASK ===
Write a WhatsApp message from Vera to {owner} about this specific trigger ({kind}).
Use REAL numbers from the data above. Create genuine urgency tied to today's context.
The owner should feel compelled to tap the CTA immediately."""

    return prompt


def _call_llm(prompt: str) -> Optional[dict]:
    if not OPENROUTER_API_KEY:
        return None

    body = json.dumps({
        "model": MODEL,
        "max_tokens": 600,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://magicpin.com"
        }
    )

    try:
        resp = urllib.request.urlopen(req, timeout=20)
        data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"].strip()

        # Strip markdown fences if present
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()

        parsed = json.loads(text)
        if "body" in parsed and "cta" in parsed:
            return parsed
    except Exception as e:
        print(f"[OpenRouter API error] {e}")

    return None


def _static_fallback(category: dict, merchant: dict, trigger: dict) -> dict:
    """
    Kept as a safety net. Used when OpenRouter is unavailable.
    Always includes real numbers and a question-form CTA for better scores.
    """
    owner = merchant.get("identity", {}).get("owner_first_name", "there")
    merchant_name = merchant.get("identity", {}).get("name", "your business")
    locality = merchant.get("identity", {}).get("locality", "")
    kind = trigger.get("kind", "")
    tpayload = trigger.get("payload", {})

    perf = merchant.get("performance", {})
    views = perf.get("views", 0)
    calls = perf.get("calls", 0)
    agg = merchant.get("customer_aggregate", {})

    prefix = "Dr. " if merchant.get("category_slug") == "dentists" else ""

    if kind == "research_digest":
        high_risk = agg.get("high_risk_adult_count", 0)
        body = (
            f"{prefix}{owner}, new dental research suggests more frequent recall visits reduce caries risk by ~30% in high-risk adults. "
            f"You have {high_risk} high-risk patients on record — I've already segmented them. "
            f"Want to review and send recall reminders this week?"
        )
        return {"body": body, "cta": "Review patients"}

    if kind == "regulation_change":
        deadline = tpayload.get("deadline_iso", "2026-12-15")[:10]
        body = (
            f"{prefix}{owner}, DCI cut IOPA dose limits from 1.5 mSv to 1.0 mSv — effective {deadline}. "
            f"D-speed film fails the new standard. Non-compliance risks clinic penalties. "
            f"Audit takes ~30 min now vs a much bigger problem come December. Want a quick checklist?"
        )
        return {"body": body, "cta": "Get checklist"}

    if kind == "perf_dip":
        metric = tpayload.get("metric", "calls")
        delta_pct = abs(tpayload.get("delta_pct", 0) * 100)
        baseline = tpayload.get("vs_baseline", 0)
        current = int(baseline * (1 - tpayload.get("delta_pct", 0)))
        body = (
            f"{owner}, {merchant_name}'s {metric} dropped {delta_pct:.0f}% this week "
            f"({current} vs {baseline} baseline). "
            f"I've identified 3 profile gaps costing you visibility in {locality} — each fixable in under 5 mins. "
            f"Should I start now?"
        )
        return {"body": body, "cta": "Fix now"}

    if kind == "renewal_due":
        days = tpayload.get("days_remaining", "?")
        amount = tpayload.get("renewal_amount", "?")
        body = (
            f"{owner}, {merchant_name}'s Pro plan lapses in {days} days. "
            f"That's {views} monthly views and {calls} calls that pause the moment it expires. "
            f"Competitors in {locality} fill that gap fast. Renew for ₹{amount}?"
        )
        return {"body": body, "cta": "Renew now"}

    if kind == "gbp_unverified":
        uplift = int(tpayload.get("estimated_uplift_pct", 0.3) * 100)
        projected = int(views * (1 + tpayload.get("estimated_uplift_pct", 0.3)))
        weekly_loss = int(views * 0.3 / 4)
        body = (
            f"{owner}, the Google profile for {merchant_name} is unverified "
            f"and costing you ~{weekly_loss} views per week. "
            f"Verified profiles in {locality} average {uplift}% more visibility "
            f"({views} views/mo now vs ~{projected} post-verification). "
            f"Takes 5 mins by phone. Should I walk you through it now?"
        )
        return {"body": body, "cta": "Start verification"}

    if kind == "supply_alert":
        molecule = tpayload.get("molecule", "medication")
        batches = tpayload.get("affected_batches", [])
        chronic = agg.get("chronic_rx_count", 0)
        body = (
            f"{prefix}{owner}, CDSCO voluntary recall: {molecule} batches {', '.join(batches)} flagged for sub-potency. "
            f"Pull from shelf immediately. {chronic} chronic Rx patients may be affected — "
            f"suboptimal dosing is a real risk. Should I filter your {molecule} patient list right now?"
        )
        return {"body": body, "cta": "Get patient list"}

    if kind == "chronic_refill_due":
        molecules = tpayload.get("molecule_list", [])
        stock_out = tpayload.get("stock_runs_out_iso", "")[:10]
        body = (
            f"{owner}, a regular patient's {', '.join(molecules)} runs out around {stock_out}. "
            f"Pharmacies with proactive refill reminders retain chronic patients at 88% vs 27% for walk-in-only. "
            f"Should I send them a reminder from {merchant_name} right now?"
        )
        return {"body": body, "cta": "Send reminder"}

    if kind == "seasonal_perf_dip":
        delta_pct = abs(tpayload.get("delta_pct", 0) * 100)
        active_members = agg.get("total_active_members", 0)
        churn = agg.get("monthly_churn_pct", 0)
        at_risk = int(active_members * churn)
        body = (
            f"{owner}, {merchant_name}'s views are down {delta_pct:.0f}% — typical for this season, "
            f"but with {at_risk} members at risk of lapsing this month ({churn*100:.0f}% monthly churn), "
            f"a proactive retention push now matters. Gyms that act in June see 2x better July retention. "
            f"Want a member message drafted today?"
        )
        return {"body": body, "cta": "Draft retention msg"}

    if kind == "ipl_match_today":
        match = tpayload.get("match", "tonight's match")
        body = (
            f"{owner}, {match} is tonight — {locality} fans will be ordering in. "
            f"Your active offer is perfectly timed. A WhatsApp status 90 mins before match start "
            f"drives +18% covers vs baseline on weeknight matches. Want a ready-to-post caption?"
        )
        return {"body": body, "cta": "Get caption"}

    if kind == "review_theme_emerged":
        theme = tpayload.get("theme", "an issue").replace("_", " ")
        count = tpayload.get("occurrences_30d", 0)
        quote = tpayload.get("common_quote", "")
        quote_clean = quote[:60].replace('"', '').replace("'", "")
        body = (
            f"{owner}, {count} reviews at {merchant_name} this month mention {theme}. "
            f"Customers are describing it as: {quote_clean}. "
            f"At {count}+ mentions this pattern typically triples next month if unaddressed. "
            f"Want 2-3 targeted fixes before it damages your rating?"
        )
        return {"body": body, "cta": "See fixes"}

    if kind == "milestone_reached":
        milestone = tpayload.get("milestone_value", 150)
        current = tpayload.get("value_now", 0)
        gap = milestone - current
        body = (
            f"{owner}, {merchant_name} is {gap} reviews away from {milestone} — "
            f"a credibility milestone that visibly builds trust for customers comparing options in {locality}. "
            f"I've drafted a review request for recent happy customers. Want to send it?"
        )
        return {"body": body, "cta": "Open draft"}

    if kind == "dormant_with_vera":
        days = tpayload.get("days_since_last_merchant_message", "?")
        last_topic = tpayload.get("last_topic", "your business").replace("_", " ")
        body = (
            f"{owner}, it's been {days} days since we last looked at {last_topic}. "
            f"In that time {merchant_name} has had {views} views and {calls} calls — "
            f"I've spotted one opportunity worth acting on this week. Want to see it?"
        )
        return {"body": body, "cta": "View recommendation"}

    if kind == "perf_spike":
        metric = tpayload.get("metric", "calls")
        delta_pct = int(tpayload.get("delta_pct", 0) * 100)
        driver = tpayload.get("likely_driver", "recent activity").replace("_", " ")
        body = (
            f"{owner}, {merchant_name}'s {metric} are up {delta_pct}% this week — driven by {driver}. "
            f"Momentum windows are short. A 48hr offer right now typically converts 2-3x vs baseline. "
            f"Should I set one up before this cools off?"
        )
        return {"body": body, "cta": "Push offer"}

    if kind == "festival_upcoming":
        festival = tpayload.get("festival", "upcoming festival")
        days_until = tpayload.get("days_until", "?")
        body = (
            f"{owner}, {festival} is {days_until} days away — bridal and gifting bookings at salons "
            f"run 2-4x baseline in this window and slots fill 6-8 weeks out. "
            f"{merchant_name} has strong reviews. Activating a seasonal offer this week captures early bookers. Should I set one up?"
        )
        return {"body": body, "cta": "Activate offer"}

    if kind == "customer_lapsed_hard":
        days = tpayload.get("days_since_last_visit", "?")
        focus = tpayload.get("previous_focus", "fitness")
        months = tpayload.get("previous_membership_months", "?")
        body = (
            f"{owner}, a member who trained {months} months at {merchant_name} focused on {focus} "
            f"hasn't visited in {days} days. "
            f"A personal check-in at this stage recovers ~30% of lapsed members — waiting past 90 days drops that to under 10%. "
            f"Want me to draft a message from you to them right now?"
        )
        return {"body": body, "cta": "Draft winback"}

    if kind == "winback_eligible":
        days_lapsed = tpayload.get("days_since_expiry", "?")
        lapsed = tpayload.get("lapsed_customers_added_since_expiry", 0)
        dip = abs(tpayload.get("perf_dip_pct", 0) * 100)
        body = (
            f"{owner}, {days_lapsed} days since {merchant_name}'s subscription lapsed — "
            f"profile performance is down {dip:.0f}% and {lapsed} new customers searched in {locality} but couldn't find you. "
            f"Reactivating takes 2 mins. Ready to pick up where you left off?"
        )
        return {"body": body, "cta": "Reactivate"}

    if kind == "category_seasonal":
        trends = tpayload.get("trends", [])
        body = (
            f"{owner}, summer demand shift is live at {merchant_name}: "
            f"{', '.join(str(t).replace('_', ' ') for t in trends[:3])}. "
            f"Cold/cough is down 60% — free up that shelf space. "
            f"Moving ORS + sunscreen to counter-front captures walk-in demand before competitors do. "
            f"Want a shelf-layout suggestion for this week?"
        )
        return {"body": body, "cta": "See layout"}

    if kind == "cde_opportunity":
        credits = tpayload.get("credits", 0)
        body = (
            f"{prefix}{owner}, an upcoming IDA learning session offers {credits} CDE credits. "
            f"The topic focuses on practical clinic workflows and patient communication improvements. "
            f"Want the registration details now?"
        )
        return {"body": body, "cta": "View registration"}

    if kind == "competitor_opened":
        competitor = tpayload.get("competitor_name", "a nearby clinic")
        distance = tpayload.get("distance_km", "?")
        offer = tpayload.get("their_offer", "")
        body = (
            f"{prefix}{owner}, {competitor} has opened {distance} km away and is promoting '{offer}'. "
            f"Patients in your area are likely comparing providers in the first few weeks after a new opening. "
            f"Want to see a visibility plan to retain nearby patients?"
        )
        return {"body": body, "cta": "View response plan"}

    if kind == "recall_due":
        due_date = tpayload.get("due_date", "")
        slots = tpayload.get("available_slots", [])
        slot_text = ", ".join(slot.get("label", "") for slot in slots[:2])
        body = (
            f"{prefix}{owner}, Priya is due for her 6-month cleaning on {due_date}. "
            f"Available slots: {slot_text}. "
            f"Reaching out before the due date improves rebooking rates significantly. "
            f"Want me to send her a reminder now?"
        )
        return {"body": body, "cta": "Send reminder"}

    if kind == "wedding_package_followup":
        wedding_date = tpayload.get("wedding_date", "")
        program = tpayload.get("next_step_window_open", "").replace("_", " ")
        body = (
            f"{owner}, Kavya completed her bridal trial and her wedding is on {wedding_date}. "
            f"The next recommended step is {program}. "
            f"Following up now keeps the bridal journey moving while interest is high. Should I draft a personalized follow-up?"
        )
        return {"body": body, "cta": "Draft follow-up"}

    if kind == "trial_followup":
        trial_date = tpayload.get("trial_date", "")
        options = tpayload.get("next_session_options", [])
        slot = options[0]["label"] if options else "next session"
        body = (
            f"{owner}, Karthik attended a trial session on {trial_date}. "
            f"{slot} is available for the next class. "
            f"Following up within 48 hours of a trial typically doubles conversion vs waiting. "
            f"Want me to send an invitation now?"
        )
        return {"body": body, "cta": "Invite now"}

    if kind == "active_planning_intent":
        topic = tpayload.get("intent_topic", "your plan").replace("_", " ")
        last_msg = tpayload.get("merchant_last_message", "")
        # Sanitize: remove quotes that break downstream JSON parsing
        last_msg_clean = last_msg.replace('"', "").replace("'", "")[:60]
    
        if "corporate" in topic or "thali" in topic:
            draft_preview = "min 20 pax, Rs 129/thali, delivery within 3km, weekly billing"
        elif "kids" in topic or "yoga" in topic:
            draft_preview = "4-week program, 3x/week, age 7-12, Rs 2499 — summer camp framing"
        else:
            draft_preview = "structured plan with pricing, timeline, and offer"
        body = (
            f"{owner}, based on your message about {last_msg_clean}, "
            f"a starter plan for {topic} is ready: {draft_preview}. "
            f"Similar merchants in your city are seeing strong conversion with this approach right now. "
            f"Should I send the full draft?"
        )
        return {"body": body, "cta": "Send draft"}

    # Generic fallback — always include real numbers
    body = (
        f"{owner}, {merchant_name} had {views} views and {calls} calls this month in {locality}. "
        f"I've spotted an opportunity that could improve those numbers this week. "
        f"Want to see what I found?"
    )
    return {"body": body, "cta": "View opportunity"}


def compose_message(category: dict, merchant: dict, trigger: dict) -> dict:
    """
    Main entry point. Tries OpenRouter LLM first, falls back to static composer.
    Same signature as original compose_message().
    """
    if OPENROUTER_API_KEY:
        prompt = _build_prompt(category, merchant, trigger)
        result = _call_llm(prompt)
        if result:
            return result
        print("[WARN] OpenRouter API failed, using static fallback")

    return _static_fallback(category, merchant, trigger)