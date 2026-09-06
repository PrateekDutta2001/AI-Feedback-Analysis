"""Generate realistic training and dummy feedback datasets."""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.app.config import get_settings

PRODUCTS = [
    "InsightPay",
    "InsightCloud",
    "InsightMobile",
    "InsightCRM",
    "InsightAnalytics",
    "InsightSecure",
    "InsightChat",
    "InsightPortal",
]
DEPARTMENTS = [
    "Customer Support",
    "Operations",
    "Product",
    "Engineering",
    "Sales",
    "Finance",
    "HR",
]
CHANNELS = [
    "Website",
    "Mobile App",
    "Email",
    "Call Center",
    "Social Media",
    "Survey",
    "Chat",
    "Internal",
]
LOCATIONS = [
    "Ahmedabad",
    "Surat",
    "Mumbai",
    "Delhi",
    "Bangalore",
    "Hyderabad",
    "Pune",
    "Chennai",
    "Kolkata",
    "Jaipur",
    "London",
    "New York",
    "Singapore",
    "Dubai",
]
SEGMENTS = ["Enterprise", "SMB", "Startup", "Consumer", "Partner", "Internal"]
STATUSES = ["open", "in_progress", "resolved", "closed"]

TRAINING_BANK: list[dict[str, str]] = []


def _add(text: str, sentiment: str, emotion: str, category: str, intent: str) -> None:
    TRAINING_BANK.append(
        {
            "text": text,
            "sentiment": sentiment,
            "emotion": emotion,
            "category": category,
            "intent": intent,
        }
    )


def _build_training_bank() -> list[dict[str, str]]:
    if TRAINING_BANK:
        return TRAINING_BANK

    positive_delivery = [
        "Delivery arrived earlier than promised and the package was intact.",
        "Courier service was excellent and I received my order on time.",
        "Shipping was fast and the tracking updates were accurate.",
        "Loved how quickly the parcel reached my office in {city}.",
        "The delivery experience for {product} was smooth from checkout to doorstep.",
    ]
    negative_delivery = [
        "Delivery was extremely late and customer support did not respond.",
        "The courier lost my package and nobody provided a refund update.",
        "Shipping delay of five days ruined the rollout of {product}.",
        "My order never arrived and the tracking page stayed stuck.",
        "Late delivery in {city} is becoming a repeated issue for us.",
        "The package arrived damaged after a long delay.",
        "Delivery partner missed two scheduled slots without notice.",
    ]
    positive_support = [
        "Customer support resolved my ticket in under an hour.",
        "The agent was patient, knowledgeable, and genuinely helpful.",
        "Live chat support walked me through the setup perfectly.",
        "I am impressed with how quickly the helpdesk closed my request.",
    ]
    negative_support = [
        "I waited two days and customer support still has not replied.",
        "The support agent closed my ticket without solving anything.",
        "Response time is unacceptable and I had to repeat my issue three times.",
        "Nobody from support called me back after promising an update.",
        "Your helpdesk keeps transferring me between departments.",
    ]
    positive_product = [
        "The new {product} features are intuitive and save our team hours.",
        "Build quality of {product} exceeded our expectations.",
        "We love the reliability of {product} during peak hours.",
        "Product onboarding was simple and the value was immediate.",
    ]
    negative_product = [
        "The latest {product} release feels unfinished and buggy.",
        "Product quality has declined after the last update.",
        "Several core {product} features are missing for enterprise use.",
        "The hardware accessory arrived with a manufacturing defect.",
    ]
    positive_payment = [
        "Checkout was seamless and the card payment succeeded instantly.",
        "Invoicing in {product} is clear and finance approved it quickly.",
        "Refund was processed faster than I expected.",
    ]
    negative_payment = [
        "Payment failed twice at checkout and the amount was still held.",
        "I was charged twice and the refund is still pending.",
        "Billing invoice does not match the contracted pricing.",
        "Card verification keeps failing on the mobile checkout page.",
        "Unauthorized charge appeared on our corporate card after renewal.",
    ]
    pricing = [
        "The pricing is far too high for the current feature set.",
        "Please reconsider the annual price increase for SMB customers.",
        "We need a more transparent pricing page with add-on costs.",
        "The plan is expensive compared with competitors but still usable.",
        "Happy with the value, the price feels fair for {product}.",
    ]
    technical = [
        "The dashboard crashes whenever I export a large CSV.",
        "Users cannot login after the last authentication update.",
        "API timeouts are breaking our nightly sync jobs.",
        "The mobile app crashes on Android 14 during search.",
        "We keep seeing a 500 error on the reports page.",
        "Bug: notifications never mark themselves as read.",
    ]
    ux = [
        "The new navigation is confusing and I cannot find settings.",
        "Please simplify the filter panel, it is overcrowded.",
        "Love the cleaner layout, the interface is much easier now.",
        "Dark mode contrast on charts is hard to read.",
        "The onboarding tooltip blocked the save button.",
    ]
    performance = [
        "The application is extremely slow during morning peak hours.",
        "Report generation takes more than four minutes.",
        "Pages load quickly even with large datasets, great work.",
        "Search latency has improved after the last release.",
        "Timeouts on the analytics page make the tool unusable.",
    ]
    security = [
        "We detected suspicious login attempts on admin accounts.",
        "Please add hardware key support for enterprise SSO.",
        "Password reset emails are delayed which is a security risk.",
        "Unauthorized access alert fired twice last night.",
        "Appreciate the new audit trail, it helps our compliance team.",
    ]
    account = [
        "I cannot reset my password and the account is locked.",
        "Please update our billing admin on the enterprise account.",
        "User provisioning from SSO is creating duplicate accounts.",
        "How do I deactivate a former employee account?",
    ]
    docs = [
        "The API documentation is missing the pagination examples.",
        "Implementation guide is clear and helped us go live faster.",
        "Please publish a changelog for the latest webhook fields.",
        "Docs still mention a deprecated authentication header.",
    ]
    service = [
        "Onsite implementation service was professional and thorough.",
        "The professional services team missed the agreed milestone.",
        "Training session for new managers was excellent.",
        "Onboarding consultant did not understand our workflow.",
    ]
    questions = [
        "How do I export filtered analytics to CSV?",
        "What is the SLA for priority one incidents?",
        "Can {product} integrate with our existing billing system?",
        "Where can I find the data retention policy?",
    ]
    suggestions = [
        "It would help if you added weekly digest emails for managers.",
        "Consider a bulk reassign option for open tickets.",
        "A comparison view across products would be useful.",
        "Please allow saved filters on the feedback explorer.",
    ]
    feature_requests = [
        "Feature request: role-based alert routing by department.",
        "Please add Slack notifications for critical feedback.",
        "We need multi-currency invoices in {product}.",
        "Add an API endpoint for historical sentiment trends.",
    ]
    praise = [
        "Outstanding release, the team should be proud of {product}.",
        "Thank you for the rapid hotfix, everything is stable again.",
        "Your onboarding specialist made our go-live painless.",
        "I recommend {product} to every operations leader I meet.",
    ]
    information = [
        "Sharing that our usage will increase next quarter.",
        "This is an FYI that the Mumbai office is migrating next week.",
        "We completed internal training on the new workflow.",
        "Noting that the survey was submitted by the finance team.",
    ]
    requests = [
        "Please send the latest security questionnaire.",
        "Can you schedule a call with our procurement team?",
        "We need access for three additional analysts this week.",
        "Kindly share the incident report from last Friday.",
    ]
    hr_internal = [
        "The internal portal for leave requests is confusing.",
        "Payroll support answered quickly and corrected the error.",
        "New hire documentation is incomplete for remote staff.",
    ]

    for text in positive_delivery:
        _add(text, "positive", "satisfaction", "Delivery", "Praise")
    for text in negative_delivery:
        _add(text, "negative", "frustration", "Delivery", "Complaint")
    for text in positive_support:
        _add(text, "positive", "satisfaction", "Customer Support", "Praise")
    for text in negative_support:
        _add(text, "negative", "frustration", "Customer Support", "Complaint")
    for text in positive_product:
        _add(text, "positive", "joy", "Product", "Praise")
    for text in negative_product:
        _add(text, "negative", "disappointment", "Product", "Complaint")
    for text in positive_payment:
        _add(text, "positive", "satisfaction", "Payment", "Praise")
    for text in negative_payment:
        _add(text, "negative", "anger", "Payment", "Complaint")
    for text in pricing[:3]:
        _add(text, "negative", "disappointment", "Pricing", "Suggestion")
    _add(pricing[3], "neutral", "neutral", "Pricing", "Information")
    _add(pricing[4], "positive", "satisfaction", "Pricing", "Praise")
    for text in technical:
        _add(text, "negative", "frustration", "Technical Issue", "Bug Report")
    _add(ux[0], "negative", "confusion", "UX/UI", "Complaint")
    _add(ux[1], "neutral", "confusion", "UX/UI", "Suggestion")
    _add(ux[2], "positive", "joy", "UX/UI", "Praise")
    _add(ux[3], "negative", "disappointment", "UX/UI", "Bug Report")
    _add(ux[4], "negative", "frustration", "UX/UI", "Bug Report")
    _add(performance[0], "negative", "frustration", "Performance", "Complaint")
    _add(performance[1], "negative", "disappointment", "Performance", "Bug Report")
    _add(performance[2], "positive", "satisfaction", "Performance", "Praise")
    _add(performance[3], "positive", "satisfaction", "Performance", "Praise")
    _add(performance[4], "negative", "anger", "Performance", "Complaint")
    _add(security[0], "negative", "anger", "Security", "Bug Report")
    _add(security[1], "neutral", "neutral", "Security", "Feature Request")
    _add(security[2], "negative", "frustration", "Security", "Complaint")
    _add(security[3], "negative", "anger", "Security", "Complaint")
    _add(security[4], "positive", "satisfaction", "Security", "Praise")
    for text in account[:3]:
        _add(text, "negative", "frustration", "Account", "Request")
    _add(account[3], "neutral", "confusion", "Account", "Question")
    _add(docs[0], "negative", "confusion", "Documentation", "Bug Report")
    _add(docs[1], "positive", "satisfaction", "Documentation", "Praise")
    _add(docs[2], "neutral", "neutral", "Documentation", "Request")
    _add(docs[3], "negative", "disappointment", "Documentation", "Bug Report")
    _add(service[0], "positive", "satisfaction", "Service", "Praise")
    _add(service[1], "negative", "disappointment", "Service", "Complaint")
    _add(service[2], "positive", "joy", "Service", "Praise")
    _add(service[3], "negative", "frustration", "Service", "Complaint")
    for text in questions:
        _add(text, "neutral", "confusion", "Other", "Question")
    for text in suggestions:
        _add(text, "neutral", "neutral", "Other", "Suggestion")
    for text in feature_requests:
        _add(text, "neutral", "neutral", "Product", "Feature Request")
    for text in praise:
        _add(text, "positive", "joy", "Product", "Praise")
    for text in information:
        _add(text, "neutral", "neutral", "Other", "Information")
    for text in requests:
        _add(text, "neutral", "neutral", "Customer Support", "Request")
    for text in hr_internal:
        _add(text, "neutral", "confusion", "Other", "Suggestion")

    extras = [
        ("I am delighted with the onboarding journey for {product}.", "positive", "joy", "Service", "Praise"),
        ("Absolutely thrilled, this exceeded every expectation.", "positive", "joy", "Product", "Praise"),
        ("Happy to see the refund completed without extra emails.", "positive", "satisfaction", "Payment", "Praise"),
        ("The product is okay, nothing special but it works.", "neutral", "neutral", "Product", "Information"),
        ("Average experience overall, neither good nor bad.", "neutral", "neutral", "Service", "Information"),
        ("Fine for now, we will evaluate again next quarter.", "neutral", "neutral", "Product", "Information"),
        ("I am so angry about the failed payroll deduction.", "negative", "anger", "Payment", "Complaint"),
        ("This is the worst outage we have had this year.", "negative", "anger", "Technical Issue", "Bug Report"),
        ("Sad to see the quality drop after years of loyalty.", "negative", "sadness", "Product", "Complaint"),
        ("I am sad that the service we relied on is gone.", "negative", "sadness", "Service", "Complaint"),
        ("Feeling sad about losing access to historical reports.", "negative", "sadness", "Product", "Complaint"),
        ("It is sad that our favorite workflow was removed.", "negative", "sadness", "UX/UI", "Complaint"),
        ("We are sad to churn after five years with {product}.", "negative", "sadness", "Product", "Complaint"),
        ("Heartbroken that the promised migration support never arrived.", "negative", "sadness", "Customer Support", "Complaint"),
        ("I miss the old interface; the change left our team unhappy.", "negative", "sadness", "UX/UI", "Complaint"),
        ("Sorry to see reliability decline, this used to be dependable.", "negative", "sadness", "Performance", "Complaint"),
        ("I feel disappointed that the promised feature never shipped.", "negative", "disappointment", "Product", "Complaint"),
        ("Confused about how seats are counted on the invoice.", "neutral", "confusion", "Pricing", "Question"),
        ("Unable to understand the new permission model.", "negative", "confusion", "UX/UI", "Question"),
        ("Please add export to JSON for compliance reviews.", "neutral", "neutral", "Product", "Feature Request"),
        ("Is two-factor authentication mandatory for partners?", "neutral", "confusion", "Security", "Question"),
        ("Authentication failures have increased since Tuesday.", "negative", "frustration", "Technical Issue", "Bug Report"),
        ("Mobile users cannot complete payment on InsightPay.", "negative", "frustration", "Payment", "Bug Report"),
        ("Delivery SLA in Ahmedabad and Surat is consistently missed.", "negative", "frustration", "Delivery", "Complaint"),
        ("Call center hold time is over twenty minutes.", "negative", "anger", "Customer Support", "Complaint"),
        ("Survey follow-up email never arrived.", "negative", "disappointment", "Customer Support", "Complaint"),
        ("Internal HR form submission fails on Safari.", "negative", "frustration", "Technical Issue", "Bug Report"),
        ("Sales demo environment was prepared perfectly.", "positive", "satisfaction", "Service", "Praise"),
        ("Documentation search finally returns relevant pages.", "positive", "satisfaction", "Documentation", "Praise"),
        ("We need weekend coverage from customer support.", "neutral", "neutral", "Customer Support", "Request"),
        ("Can you confirm data residency for the Singapore workspace?", "neutral", "neutral", "Security", "Question"),
        ("The chatbot gave irrelevant answers about refund policy.", "negative", "frustration", "Customer Support", "Complaint"),
        ("Loved the in-app guidance, first-time users finished setup quickly.", "positive", "joy", "UX/UI", "Praise"),
        ("Performance is acceptable on desktop but poor on mobile.", "neutral", "disappointment", "Performance", "Suggestion"),
        ("A duplicate charge appeared after the free trial ended.", "negative", "anger", "Payment", "Complaint"),
        ("Please investigate why webhooks are delivered twice.", "negative", "confusion", "Technical Issue", "Bug Report"),
        ("Great job reducing login time after the identity upgrade.", "positive", "satisfaction", "Account", "Praise"),
    ]
    for row in extras:
        _add(*row)

    # Expand with product/city substitutions so the trainer sees lexical variety.
    expanded: list[dict[str, str]] = []
    for row in TRAINING_BANK:
        if "{product}" in row["text"] or "{city}" in row["text"]:
            for product in PRODUCTS:
                for city in ("Ahmedabad", "Surat", "Mumbai", "London"):
                    expanded.append(
                        {
                            **row,
                            "text": row["text"].format(product=product, city=city),
                        }
                    )
        else:
            expanded.append(row)
            if random.random() < 0.35:
                product = random.choice(PRODUCTS)
                expanded.append({**row, "text": f"{row['text']} This was reported for {product}."})
    TRAINING_BANK.clear()
    TRAINING_BANK.extend(expanded)
    return TRAINING_BANK


TEMPLATES = {
    "negative": [
        "Delivery was extremely late and customer support did not respond.",
        "The {product} checkout failed and I was still charged.",
        "I am frustrated that the {product} app crashes during payment.",
        "Support never called back after I reported a critical outage.",
        "Package for {product} arrived damaged in {city}.",
        "We cannot login to {product} since the last update.",
        "Billing error created an unauthorized charge on our card.",
        "Response time from customer support is getting worse every week.",
        "The courier missed the delivery window three times in {city}.",
        "Authentication failures are blocking our entire sales team.",
        "Refund for a failed {product} payment is still pending.",
        "The latest release introduced a severe performance regression.",
        "I am angry that the ticket was closed without a resolution.",
        "Documentation is outdated and caused a production misconfiguration.",
        "Mobile users report they cannot complete signup on {product}.",
        "Security alert fired after suspicious admin logins.",
        "Price increase was communicated poorly and feels unjustified.",
        "Call center agents read from a script and did not understand the issue.",
        "Search is too slow to be usable during business hours.",
        "Duplicate invoices were sent to finance after renewal.",
    ],
    "positive": [
        "Loved the new {product} dashboard, it is clean and fast.",
        "Customer support resolved our incident in twenty minutes.",
        "Delivery to {city} was earlier than the estimated date.",
        "The onboarding specialist made {product} easy to adopt.",
        "Payment reconciliation finally works without manual edits.",
        "Great improvement in mobile performance this month.",
        "Documentation update saved our engineering team hours.",
        "I am delighted with the quality of the latest {product} release.",
        "Sales team prepared a thoughtful demo for our executives.",
        "Refund was issued quickly and with a clear explanation.",
        "The interface redesign is intuitive and reduced training time.",
        "Appreciate the proactive outage communication.",
        "InsightSecure audit logs are exactly what compliance needed.",
        "Chat support was knowledgeable and patient.",
        "We are happy with the reliability of {product} this quarter.",
    ],
    "neutral": [
        "The {product} rollout is scheduled for next Monday in {city}.",
        "Please confirm whether SSO is enabled for partner accounts.",
        "How do I export department analytics for last quarter?",
        "We may add twenty more seats if the trial goes well.",
        "Sharing an FYI that finance will review invoices tomorrow.",
        "Can you schedule a training session for the operations team?",
        "It would help to have saved filters on the explorer table.",
        "Feature request: webhook retries with exponential backoff.",
        "Average experience so far, we are still evaluating {product}.",
        "Where can I find the data retention policy?",
        "Consider adding a weekly digest for managers.",
        "Need access for two additional analysts this week.",
        "The current plan is acceptable but we will compare alternatives.",
        "Is there a sandbox for InsightPay chargebacks?",
        "Noting that the internal survey was completed by HR.",
    ],
}

FOLLOW_ONS = [
    "This happened after the latest update.",
    "Please treat this as high priority.",
    "We have seen this twice already.",
    "The issue started last Thursday.",
    "Our enterprise account is affected.",
    "I attached screenshots in the original ticket.",
    "This is impacting customers in {city}.",
    "The team mentioned {product} in the weekly review.",
    "A workaround exists but it is not acceptable long term.",
    "I am following up because there was no response.",
]


def _unique_text(sentiment: str, rng: random.Random) -> str:
    base = rng.choice(TEMPLATES[sentiment]).format(
        product=rng.choice(PRODUCTS),
        city=rng.choice(LOCATIONS),
    )
    extra = rng.choice(FOLLOW_ONS).format(
        product=rng.choice(PRODUCTS),
        city=rng.choice(LOCATIONS),
    )
    openers = [
        "",
        "Hello team, ",
        "Hi, ",
        "Quick update: ",
        "To be clear, ",
        "For the record, ",
    ]
    closers = [
        "",
        " Thanks.",
        " Please advise.",
        " Looking forward to a fix.",
        " Sharing this from the field.",
        " Logged by the duty manager.",
    ]
    return f"{rng.choice(openers)}{base} {extra}{rng.choice(closers)}".strip()


def generate_training_csv(path: Path) -> int:
    rows = _build_training_bank()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["text", "sentiment", "emotion", "category", "intent"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def generate_dummy_csv(path: Path, count: int = 2200) -> int:
    rng = random.Random(42)
    start = datetime.now(timezone.utc) - timedelta(days=250)
    rows: list[dict[str, str]] = []
    weights = [("negative", 0.38), ("positive", 0.34), ("neutral", 0.28)]

    for index in range(count):
        sentiment = rng.choices([item[0] for item in weights], weights=[item[1] for item in weights])[0]
        text = _unique_text(sentiment, rng)
        rating_map = {"positive": rng.choice([4, 5, 5]), "neutral": rng.choice([3, 3, 4]), "negative": rng.choice([1, 2, 2])}
        day = start + timedelta(days=rng.randint(0, 250), hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
        product = rng.choice(PRODUCTS)
        department = rng.choice(DEPARTMENTS)
        if "delivery" in text.lower() or "courier" in text.lower():
            department = "Operations"
        elif "support" in text.lower() or "ticket" in text.lower():
            department = "Customer Support"
        elif "crash" in text.lower() or "login" in text.lower() or "bug" in text.lower():
            department = "Engineering"
        rows.append(
            {
                "feedback_id": f"FB-{10000 + index}",
                "customer_id": f"CU-{rng.randint(1000, 9999)}",
                "text": text,
                "date": day.isoformat(),
                "product": product,
                "department": department,
                "channel": rng.choice(CHANNELS),
                "location": rng.choice(LOCATIONS),
                "segment": rng.choice(SEGMENTS),
                "rating": str(rating_map[sentiment]),
                "status": rng.choices(STATUSES, weights=[0.38, 0.22, 0.28, 0.12])[0],
            }
        )

    # Intentional near-duplicates for similarity demos.
    seed_duplicates = [
        "Delivery was extremely late and customer support did not respond. This happened after the latest update.",
        "Delivery was extremely late and customer support did not respond. We have seen this twice already.",
        "Delivery was extremely late and the support team did not respond to my follow-up.",
        "I cannot login to InsightPay since the last update. Please treat this as high priority.",
        "We cannot login to InsightPay since the last update. Please treat this as high priority.",
        "Authentication failures are blocking our entire sales team. The issue started last Thursday.",
        "Authentication failures have been blocking the sales team since last Thursday.",
    ]
    for offset, text in enumerate(seed_duplicates):
        rows.append(
            {
                "feedback_id": f"FB-DUP-{offset + 1}",
                "customer_id": f"CU-{2000 + offset}",
                "text": text,
                "date": (start + timedelta(days=240 + offset)).isoformat(),
                "product": "InsightPay" if "login" in text.lower() or "auth" in text.lower() else "InsightPortal",
                "department": "Customer Support" if "support" in text.lower() else "Engineering",
                "channel": "Email" if offset % 2 == 0 else "Chat",
                "location": "Ahmedabad" if offset < 3 else "Mumbai",
                "segment": "Enterprise",
                "rating": "1" if "late" in text.lower() or "cannot" in text.lower() else "2",
                "status": "open",
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "feedback_id",
        "customer_id",
        "text",
        "date",
        "product",
        "department",
        "channel",
        "location",
        "segment",
        "rating",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def ensure_datasets() -> tuple[int, int]:
    settings = get_settings()
    training = settings.data_path / "training_data.csv"
    dummy = settings.data_path / "dummy_feedback.csv"
    training_count = generate_training_csv(training) if not training.exists() else sum(1 for _ in training.open(encoding="utf-8")) - 1
    dummy_count = generate_dummy_csv(dummy) if not dummy.exists() else sum(1 for _ in dummy.open(encoding="utf-8")) - 1
    return training_count, dummy_count
