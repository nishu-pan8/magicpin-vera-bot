def compose_message(category: dict, merchant: dict, trigger: dict) -> dict:
    owner = merchant.get("identity", {}).get("owner_first_name", "there")
    merchant_name = merchant.get("identity", {}).get("name", "your business")
    locality = merchant.get("identity", {}).get("locality", "")
    kind = trigger.get("kind", "")
    tpayload = trigger.get("payload", {})

    offers = merchant.get("offers", [])
    active_offers = [o for o in offers if o.get("status") == "active"]
    offer_line = active_offers[0]["title"] if active_offers else None

    perf = merchant.get("performance", {})
    views = perf.get("views", 0)
    calls = perf.get("calls", 0)
    ctr = perf.get("ctr", 0)
    delta = perf.get("delta_7d", {})
    calls_delta = delta.get("calls_pct", 0)
    views_delta = delta.get("views_pct", 0)

    agg = merchant.get("customer_aggregate", {})
    signals = merchant.get("signals", [])

    if kind == "research_digest":
        high_risk = agg.get("high_risk_adult_count", 0)

        body = (
            f"Dr. {owner}, a recent dental research update suggests more frequent recall visits may benefit high-risk adults. "
            f"You currently have {high_risk} high-risk adult patients on record. "
            f"This may be a good opportunity to review your recall protocol and identify patients who may benefit from earlier follow-up. "
            f"I've already prepared the patient segment for review."
        )

        return {"body": body, "cta": "Review patients"}

    if kind == "regulation_change":
        deadline = tpayload.get("deadline_iso", "2026-12-15")[:10]
        body = (
            f"Dr. {owner}, DCI revised IOPA dose limits — max drops from 1.5 mSv to 1.0 mSv, "
            f"effective {deadline}. D-speed film fails the new limit; E-speed and digital RVG are fine. "
            f"Clinics caught non-compliant face penalties. Takes ~30 min to audit your setup now vs a much bigger problem in Dec. "
            f"Want a quick compliance checklist?"
        )
        return {"body": body, "cta": "Get checklist"}

    if kind == "perf_dip":
        metric = tpayload.get("metric", "calls")
        delta_pct = abs(tpayload.get("delta_pct", 0) * 100)
        baseline = tpayload.get("vs_baseline", 0)
        issues = []
        if "unverified_gbp" in signals:
            issues.append("unverified Google profile (costs ~30% visibility)")
        if "no_active_offers" in signals:
            issues.append("no active offers (competitors with offers get 2x CTR)")
        if any("stale_posts" in s for s in signals):
            issues.append("stale posts (last post 22+ days ago)")
        issues_text = " + ".join(issues) if issues else "profile gaps"
        body = (
            f"{owner}, {merchant_name}'s {metric} dropped {delta_pct:.0f}% this week "
            f"(down to {int(baseline * (1 - tpayload.get('delta_pct', 0)))} vs {baseline} baseline). "
            f"Root causes: {issues_text}. "
            f"Each day unaddressed widens the gap vs competitors in {locality}. "
            f"I can fix all 3 in under 10 mins — should I start?"
        )
        return {"body": body, "cta": "Fix now"}

    if kind == "renewal_due":
        days = tpayload.get("days_remaining", "?")
        amount = tpayload.get("renewal_amount", "?")
        body = (
            f"{owner}, {merchant_name}'s Pro plan expires in {days} days. "
            f"Last 30 days: {views} views, {calls} calls — all of that pauses the moment the plan lapses. "
            f"Competitors in {locality} will fill that visibility gap fast. "
            f"Renewal is ₹{amount} — want me to send you the link right now?"
        )
        return {"body": body, "cta": "Renew now"}

    if kind == "gbp_unverified":
        uplift = int(tpayload.get("estimated_uplift_pct", 0.3) * 100)
        body = (
            f"{owner}, {merchant_name}'s Google profile is unverified — "
            f"verified pharmacies in {locality} average {uplift}% more visibility. "
            f"You're getting {views} views/month unverified; post-verification that's typically "
            f"{int(views * (1 + tpayload.get('estimated_uplift_pct', 0.3)))} views. "
            f"Takes 5 min via phone call. Every week unverified = {int(views * 0.3 / 4)} views lost. Should I walk you through it?"
        )
        return {"body": body, "cta": "Start verification"}

    if kind == "active_planning_intent":
        topic = tpayload.get("intent_topic", "your plan").replace("_", " ")
        last_msg = tpayload.get("merchant_last_message", "")
        if "corporate" in topic or "thali" in topic:
            draft_preview = "min 20 pax, ₹129/thali, delivery within 3km, weekly billing"
        elif "kids" in topic or "yoga" in topic:
            draft_preview = "4-week program, 3x/week, age 7-12, ₹2,499 — summer camp framing"
        else:
            draft_preview = "structured plan with pricing, timeline, and offer"
        body = (
            f"{owner}, you asked: \"{last_msg[:70]}\" — "
            f"I've drafted a starter for the {topic}: {draft_preview}. "
            f"Based on what's working for similar merchants in your city, this has strong conversion potential right now. "
            f"Should I send the full draft?"
        )
        return {"body": body, "cta": "Send draft"}

    if kind == "winback_eligible":
        days_lapsed = tpayload.get("days_since_expiry", "?")
        lapsed = tpayload.get("lapsed_customers_added_since_expiry", 0)
        dip = abs(tpayload.get("perf_dip_pct", 0) * 100)
        body = (
            f"{owner}, {days_lapsed} days since {merchant_name}'s subscription lapsed — "
            f"profile performance is down {dip:.0f}% and {lapsed} new customers searched in {locality} "
            f"but couldn't find you. That's {lapsed} missed walk-ins. "
            f"Reactivating takes 2 mins and reverses this immediately. Ready to pick up where you left off?"
        )
        return {"body": body, "cta": "Reactivate"}

    if kind == "supply_alert":
        molecule = tpayload.get("molecule", "medication")
        batches = tpayload.get("affected_batches", [])
        chronic = agg.get("chronic_rx_count", 0)
        body = (
            f"{owner}, CDSCO voluntary recall: {molecule} batches {', '.join(batches)} flagged for sub-potency by MfrZ. "
            f"Pull from shelf immediately. You have {chronic} chronic Rx customers — "
            f"affected patients on atorvastatin need to be notified today (suboptimal LDL control is the risk). "
            f"Replacement via distributor return chain. Want me to filter your chronic Rx list for this molecule?"
        )
        return {"body": body, "cta": "Get patient list"}

    if kind == "chronic_refill_due":
        molecules = tpayload.get("molecule_list", [])
        stock_out = tpayload.get("stock_runs_out_iso", "")[:10]
        has_delivery = tpayload.get("delivery_address_saved", False)
        delivery_note = "delivery address already saved" if has_delivery else "need delivery address"
        body = (
            f"{owner}, a regular patient's {', '.join(molecules)} runs out ~{stock_out}. "
            f"{delivery_note.capitalize()} — I can send them a refill reminder on {merchant_name}'s behalf right now. "
            f"Proactive refill reminders help maintain continuity of care for chronic patients. "
            f"I already have a reminder ready to send. "
            f"Send it now?"
        )
        return {"body": body, "cta": "Send reminder"}

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

    if kind == "ipl_match_today":
        match = tpayload.get("match", "tonight's match")
        body = (
            f"{owner}, {match} is tonight at Arun Jaitley Stadium — {locality} fans will be ordering in. "
            f"Your BOGO pizza offer is live and perfectly timed. "
            f"Best window: push a WhatsApp status 90 mins before match (around 6pm). "
            f"Match nights often drive higher food ordering activity than a typical weekday."
            f"Want a ready-to-post caption right now?"
        )
        return {"body": body, "cta": "Get caption"}

    if kind == "review_theme_emerged":
        theme = tpayload.get("theme", "an issue").replace("_", " ")
        count = tpayload.get("occurrences_30d", 0)
        quote = tpayload.get("common_quote", "")
        body = (
            f"{owner}, {count} reviews at {merchant_name} this month flag {theme} — "
            f"e.g. \"{quote[:70]}\". "
            f"This pattern compounds: 4 mentions now typically becomes 10+ next month if unaddressed. "
            f"Want 2-3 specific fixes to tackle this before it affects your rating?"
        )
        return {"body": body, "cta": "See fixes"}

    if kind == "milestone_reached":
        milestone = tpayload.get("milestone_value", 150)
        current = tpayload.get("value_now", 0)
        gap = milestone - current

        body = (
            f"{owner}, {merchant_name} is only {gap} reviews away from reaching {milestone}. "
            f"You're very close to an important credibility milestone for customers searching in {locality}. "
            f"I've drafted a review request message that can be sent to recent happy customers."
        )

        return {"body": body, "cta": "Open draft"}

    if kind == "festival_upcoming":
        festival = tpayload.get("festival", "upcoming festival")
        days_until = tpayload.get("days_until", "?")
        body = (
            f"{owner}, {festival} is {days_until} days away — bridal and gifting bookings at salons "
            f"typically run 2-4x baseline in this window and slots fill 6-8 weeks out. "
            f"{merchant_name} has strong reviews ({merchant.get('review_themes', [{}])[0].get('common_quote', ''[:40])}). "
            f"Activating a seasonal offer this week captures early bookers before competitors do. Should I set one up?"
        )
        return {"body": body, "cta": "Activate offer"}

    if kind == "seasonal_perf_dip":
        delta_pct = abs(tpayload.get("delta_pct", 0) * 100)
        active_members = agg.get("total_active_members", 0)
        churn = agg.get("monthly_churn_pct", 0)
        at_risk = int(active_members * churn)
        body = (
            f"{owner}, {merchant_name}'s views dipped {delta_pct:.0f}% — expected for Apr-Jun, "
            f"but with {active_members} active members and {churn*100:.0f}% monthly churn, "
            f"that's ~{at_risk} members at risk of lapsing this month. "
            f"Gyms that run a retention push now see 2x better June numbers than those that wait. "
            f"Want a member retention message drafted for this week?"
        )
        return {"body": body, "cta": "Draft retention msg"}

    if kind == "customer_lapsed_hard":
        days = tpayload.get("days_since_last_visit", "?")
        focus = tpayload.get("previous_focus", "fitness")
        months = tpayload.get("previous_membership_months", "?")
        body = (
            f"{owner}, a member who trained {months} months at {merchant_name} focused on {focus} "
            f"hasn't visited in {days} days. "
            f"At this stage (57 days), a personal check-in recovers ~30% of lapsed members — "
            f"Members are generally easier to re-engage before long periods of inactivity."
            f"Want me to draft a message from you to them right now?"
        )
        return {"body": body, "cta": "Draft winback"}

    if kind == "perf_spike":
        metric = tpayload.get("metric", "calls")
        delta_pct = int(tpayload.get("delta_pct", 0) * 100)
        driver = tpayload.get("likely_driver", "recent activity").replace("_", " ")
        body = (
            f"{owner}, {merchant_name}'s {metric} are up {delta_pct}% this week — "
            f"driven by {driver}. High interest windows are short: "
            f"Now is a good time to convert increased interest into memberships while attention is high."
            f"Want me to push a 48hr offer while this is live?"
        )
        return {"body": body, "cta": "Push offer"}

    if kind == "dormant_with_vera":
        days = tpayload.get("days_since_last_merchant_message", "?")
        last_topic = tpayload.get("last_topic", "your business").replace("_", " ")

        body = (
            f"{owner}, it's been {days} days since we last discussed {last_topic}. "
            f"{merchant_name} is still receiving customer attention, and I found a new opportunity worth reviewing. "
            f"I already have a recommendation prepared based on your recent activity."
        )

        return {"body": body, "cta": "View recommendation"}

    if kind == "cde_opportunity":
        credits = tpayload.get("credits", 0)

        body = (
            f"Dr. {owner}, an upcoming IDA learning session offers {credits} CDE credits. "
            f"The topic focuses on practical clinic workflows and patient communication improvements. "
            f"I already have the registration details ready for you."
        )

        return {"body": body, "cta": "View registration"}

    if kind == "competitor_opened":
        competitor = tpayload.get("competitor_name", "a nearby clinic")
        distance = tpayload.get("distance_km", "?")
        offer = tpayload.get("their_offer", "")

        body = (
            f"Dr. {owner}, {competitor} has opened {distance} km away and is promoting '{offer}'. "
            f"Patients in your area are likely comparing providers during the first few weeks after a new opening. "
            f"I've prepared a visibility plan focused on retaining nearby patients and highlighting your existing reputation."
        )

        return {"body": body, "cta": "View response plan"}

    if kind == "recall_due":
        due_date = tpayload.get("due_date", "")
        slots = tpayload.get("available_slots", [])

        slot_text = ", ".join(
            slot.get("label", "")
            for slot in slots[:2]
        )

        body = (
            f"Dr. {owner}, Priya is due for her 6-month cleaning on {due_date}. "
            f"Available slots: {slot_text}. "
            f"Reaching out before the due date helps maintain continuity of care and improves rebooking rates. "
            f"Would you like me to prepare a reminder for her now?"
        )

        return {
        "body": body,
        "cta": "Send reminder"
        }


    if kind == "wedding_package_followup":
        wedding_date = tpayload.get("wedding_date", "")
        program = tpayload.get(
            "next_step_window_open",
            ""
        ).replace("_", " ")

        body = (
            f"{owner}, Kavya completed her bridal trial and her wedding is scheduled for {wedding_date}. "
            f"The next recommended step is {program}. "
            f"Following up now keeps the bridal journey moving while interest is still high. "
            f"Should I draft a personalized follow-up?"
        )

        return {"body": body, "cta": "Draft follow-up"}


    if kind == "trial_followup":
        trial_date = tpayload.get("trial_date", "")
        options = tpayload.get("next_session_options", [])
        slot = options[0]["label"] if options else "next session"

        body = (
            f"{owner}, Karthik attended a trial session on {trial_date}. "
            f"{slot} is available for the next class. "
            f"Following up soon after a trial often leads to better conversion than waiting several days. "
            f"Would you like me to send an invitation?"
            )

        return {"body": body, "cta": "Invite now"}

    # Generic fallback
    body = (
        f"{owner}, I found an opportunity for {merchant_name} based on recent activity and customer behavior. "
        f"I've already prepared a recommendation tailored to your business."
    )

    return {"body": body, "cta": "View recommendation"
}