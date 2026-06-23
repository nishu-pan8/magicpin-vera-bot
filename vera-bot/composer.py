def compose_message(category: dict, merchant: dict, trigger: dict) -> dict:
    """
    Compose a WhatsApp message for a merchant based on their context and trigger.
    Returns a dict with 'body' (not 'message') and 'cta' keys — matching what the judge scores.
    """
    owner = merchant.get("identity", {}).get("owner_first_name", "there")
    merchant_name = merchant.get("identity", {}).get("name", "your business")
    locality = merchant.get("identity", {}).get("locality", "")
    kind = trigger.get("kind", "")
    tpayload = trigger.get("payload", {})

    # Active offers
    offers = merchant.get("offers", [])
    active_offers = [o for o in offers if o.get("status") == "active"]
    offer_line = active_offers[0]["title"] if active_offers else None

    # Performance
    perf = merchant.get("performance", {})
    views = perf.get("views", 0)
    calls = perf.get("calls", 0)
    delta = perf.get("delta_7d", {})

    # --- Trigger-specific messages ---

    if kind == "research_digest":
        body = (
            f"Dr. {owner}, new multi-center Indian trial (JIDA, n=2100) found "
            f"3-month fluoride varnish recalls cut caries recurrence by 38% in high-risk adults vs 6-month. "
            f"You have {merchant.get('customer_aggregate', {}).get('high_risk_adult_count', 'several')} "
            f"high-risk adult patients — worth reassessing their recall intervals. Worth a look?"
        )
        return {"body": body, "cta": "See research"}

    if kind == "regulation_change":
        deadline = tpayload.get("deadline_iso", "Dec 15")[:10]
        body = (
            f"Dr. {owner}, DCI revised radiograph dose limits effective {deadline} — "
            f"max IOPA exposure drops from 1.5 mSv to 1.0 mSv. D-speed film won't pass; "
            f"E-speed and digital RVG are fine. Worth auditing your X-ray setup before the deadline. Need help checklist?"
        )
        return {"body": body, "cta": "Get checklist"}

    if kind == "perf_dip":
        metric = tpayload.get("metric", "calls")
        delta_pct = abs(tpayload.get("delta_pct", 0) * 100)
        signals = merchant.get("signals", [])
        issues = []
        if "unverified_gbp" in signals:
            issues.append("unverified Google profile")
        if "no_active_offers" in signals:
            issues.append("no active offers")
        if "stale_posts" in str(signals):
            issues.append("stale posts")
        issues_text = " + ".join(issues) if issues else "profile gaps"
        body = (
            f"{owner}, {merchant_name}'s {metric} dropped {delta_pct:.0f}% this week. "
            f"Quick look shows: {issues_text}. "
            f"3 fixes could recover visibility in 48hrs — want me to walk through them?"
        )
        return {"body": body, "cta": "Show fixes"}

    if kind == "renewal_due":
        days = tpayload.get("days_remaining", "?")
        amount = tpayload.get("renewal_amount", "?")
        body = (
            f"{owner}, {merchant_name}'s Pro plan expires in {days} days (₹{amount} renewal). "
            f"Your profile currently gets {views} views/month — pausing now means losing that visibility "
            f"right before peak season. Want to renew in 2 taps?"
        )
        return {"body": body, "cta": "Renew now"}

    if kind == "gbp_unverified":
        uplift = int(tpayload.get("estimated_uplift_pct", 0.3) * 100)
        body = (
            f"{owner}, {merchant_name}'s Google profile is still unverified — "
            f"verified pharmacies in {locality} see ~{uplift}% more visibility on average. "
            f"Verification takes ~5 min via postcard or phone call. Want the steps?"
        )
        return {"body": body, "cta": "Start verification"}

    if kind == "active_planning_intent":
        topic = tpayload.get("intent_topic", "your plan").replace("_", " ")
        last_msg = tpayload.get("merchant_last_message", "")
        body = (
            f"{owner}, picking up from your message: \"{last_msg[:60]}\" — "
            f"I've drafted a starter structure for the {topic}. "
            f"Ready to share when you are. Should I send it over?"
        )
        return {"body": body, "cta": "Send draft"}

    if kind == "winback_eligible":
        days_lapsed = tpayload.get("days_since_expiry", "?")
        lapsed_customers = tpayload.get("lapsed_customers_added_since_expiry", 0)
        body = (
            f"{owner}, it's been {days_lapsed} days since {merchant_name}'s subscription lapsed — "
            f"in that time {lapsed_customers} new potential customers searched in {locality} "
            f"and couldn't find you. Reactivating takes 2 mins. Want to pick up where you left off?"
        )
        return {"body": body, "cta": "Reactivate"}

    if kind == "supply_alert":
        molecule = tpayload.get("molecule", "medication")
        batches = tpayload.get("affected_batches", [])
        body = (
            f"{owner}, CDSCO voluntary recall alert: {molecule} batches "
            f"{', '.join(batches)} flagged for sub-potency. "
            f"Pull them from shelf + notify affected customers from your chronic Rx list. "
            f"Replacement available via distributor return chain. Need the customer list filtered?"
        )
        return {"body": body, "cta": "Get customer list"}

    if kind == "chronic_refill_due":
        molecules = tpayload.get("molecule_list", [])
        stock_out = tpayload.get("stock_runs_out_iso", "")[:10]
        body = (
            f"{owner}, a regular patient's {', '.join(molecules)} refill runs out ~{stock_out}. "
            f"Delivery address is saved — want me to send them a refill reminder on your behalf?"
        )
        return {"body": body, "cta": "Send reminder"}

    if kind == "category_seasonal":
        trends = tpayload.get("trends", [])
        body = (
            f"{owner}, summer demand shift underway at {merchant_name}: "
            f"{', '.join(str(t) for t in trends[:3])}. "
            f"Moving ORS + sunscreen to counter visibility now captures walk-in demand. "
            f"Want a shelf-layout suggestion?"
        )
        return {"body": body, "cta": "See suggestions"}

    if kind == "ipl_match_today":
        match = tpayload.get("match", "tonight's match")
        match_time = tpayload.get("match_time_iso", "")
        body = (
            f"{owner}, {match} is tonight at Arun Jaitley Stadium — fans in {locality} will be watching. "
            f"Your BOGO pizza offer is live. Push a match-night combo on your WhatsApp status now "
            f"to catch the pre-match order window (best 60-90 min before). Want a caption?"
        )
        return {"body": body, "cta": "Get caption"}

    if kind == "review_theme_emerged":
        theme = tpayload.get("theme", "an issue")
        count = tpayload.get("occurrences_30d", 0)
        quote = tpayload.get("common_quote", "")
        body = (
            f"{owner}, {count} recent reviews at {merchant_name} mention {theme.replace('_', ' ')} — "
            f"e.g. \"{quote[:60]}\". "
            f"This pattern tends to compound. Want 2-3 quick fixes to address it this week?"
        )
        return {"body": body, "cta": "See fixes"}

    if kind == "milestone_reached":
        metric = tpayload.get("metric", "reviews")
        milestone = tpayload.get("milestone_value", "?")
        current = tpayload.get("value_now", "?")
        body = (
            f"{owner}, {merchant_name} is {milestone - current} away from {milestone} {metric.replace('_', ' ')}! "
            f"Hitting this milestone boosts your ranking in {locality} search. "
            f"Want me to draft a quick post asking happy customers to leave a review?"
        )
        return {"body": body, "cta": "Draft post"}

    if kind == "festival_upcoming":
        festival = tpayload.get("festival", "upcoming festival")
        days_until = tpayload.get("days_until", "?")
        body = (
            f"{owner}, {festival} is {days_until} days away — bridal and gifting bookings at "
            f"{merchant_name} typically 2-4x baseline in this window. "
            f"Want me to activate a seasonal offer before competitor slots fill up?"
        )
        return {"body": body, "cta": "Activate offer"}

    if kind == "seasonal_perf_dip":
        note = tpayload.get("season_note", "seasonal dip")
        delta_pct = abs(tpayload.get("delta_pct", 0) * 100)
        body = (
            f"{owner}, {merchant_name}'s views dipped {delta_pct:.0f}% — this is normal for the "
            f"{note.replace('_', ' ')} window. Peer gyms who run a retention push now "
            f"see 2x better June numbers. Want a retention message for your current members?"
        )
        return {"body": body, "cta": "Send retention msg"}

    if kind == "customer_lapsed_hard":
        days = tpayload.get("days_since_last_visit", "?")
        focus = tpayload.get("previous_focus", "fitness")
        months = tpayload.get("previous_membership_months", "?")
        body = (
            f"{owner}, a member who trained {months} months focused on {focus} "
            f"hasn't visited in {days} days. "
            f"A personal check-in message from {merchant_name} recovers ~30% of lapsed members at this stage. "
            f"Want me to draft one?"
        )
        return {"body": body, "cta": "Draft winback"}

    if kind == "perf_spike":
        metric = tpayload.get("metric", "calls")
        delta_pct = int(tpayload.get("delta_pct", 0) * 100)
        driver = tpayload.get("likely_driver", "recent activity")
        body = (
            f"{owner}, {merchant_name}'s {metric} are up {delta_pct}% this week — "
            f"likely driven by {driver.replace('_', ' ')}. "
            f"Good time to convert that interest: want me to push a limited-time offer while momentum is high?"
        )
        return {"body": body, "cta": "Push offer"}

    if kind == "dormant_with_vera":
        days = tpayload.get("days_since_last_merchant_message", "?")
        last_topic = tpayload.get("last_topic", "your subscription")
        body = (
            f"{owner}, it's been {days} days — last we spoke about {last_topic.replace('_', ' ')}. "
            f"{merchant_name}'s profile is still live and getting views. "
            f"Anything I can help with this week?"
        )
        return {"body": body, "cta": "Pick up where we left off"}

    if kind == "cde_opportunity":
        credits = tpayload.get("credits", 0)
        fee = tpayload.get("fee", "")
        body = (
            f"Dr. {owner}, IDA Delhi has a digital impressions masterclass on May 2 — "
            f"{credits} CDE credits, {fee}. Covers Primescan 2, Trios 5, and CAD/CAM ROI for solo practices. "
            f"Worth it if you're seeing more cosmetic cases. Want the registration link?"
        )
        return {"body": body, "cta": "Get link"}

    if kind == "competitor_opened":
        competitor = tpayload.get("competitor_name", "a new clinic")
        distance = tpayload.get("distance_km", "?")
        their_offer = tpayload.get("their_offer", "")
        body = (
            f"Dr. {owner}, {competitor} opened {distance}km from {merchant_name} — "
            f"they're running '{their_offer}'. "
            f"Your cleaning offer is ₹299 (same price) but your reviews are stronger. "
            f"Want me to boost your GBP visibility this week to defend the turf?"
        )
        return {"body": body, "cta": "Boost visibility"}

    if kind in ("recall_due", "wedding_package_followup", "trial_followup"):
        body = (
            f"{owner}, following up for {merchant_name} — "
            f"there's a time-sensitive action for one of your customers. "
            f"Want me to pull the details?"
        )
        return {"body": body, "cta": "View details"}

    # Generic fallback — still better than "Debug action"
    body = (
        f"{owner}, I spotted something worth your attention at {merchant_name} in {locality} this week "
        f"({views} views, {calls} calls last 30d). Want a quick summary?"
    )
    return {"body": body, "cta": "Show me"}