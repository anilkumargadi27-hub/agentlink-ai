import re
from typing import List, Tuple, Set

CANONICAL_TAXONOMY = {
    "food_delivery": [
        "food delivery", "meal delivery", "restaurant orders", "restaurant discount", 
        "food offer", "order meals", "food deliveries", "dining discount"
    ],
    "merchant_promotion": [
        "merchant offer", "checkout discount", "festive sale", "merchant promotion", 
        "promotional offer", "merchant discount", "discount during", "special offer"
    ],
    "retail_checkout": [
        "online shopping", "marketplace", "ecommerce", "retail promotion", 
        "checkout offer", "shopping deal", "cart checkout", "marketplace offers"
    ],
    "upi_payment": [
        "upi", "merchant upi", "scan and pay", "upi promotion", 
        "upi payment", "qr payment", "payment gateway"
    ],
    "card_benefit": [
        "credit card", "card benefit", "card offer", "debit emi", 
        "reward points", "card cashback", "card promotion", "bank card"
    ],
    "vehicle_finance": [
        "vehicle finance", "two-wheeler loan", "vehicle emi", "auto loan", 
        "bike loan", "vehicle financing", "flexible emi", "financing options"
    ],
    "vehicle_launch": [
        "vehicle launch", "new bike model", "ev launch", "scooter launch", 
        "two-wheeler launch", "electric scooter lineup", "new vehicle"
    ]
}

def extract_canonical_topics(
    text: str, 
    supplied_topics: List[str]
) -> Tuple[List[str], List[str]]:
    """
    Extracts canonical topics using keyword/phrase mapping and validates supplied topics.
    Returns (validated_canonical_topics, derived_topics).
    """
    lower_text = text.lower()
    derived: Set[str] = set()

    for canonical, phrases in CANONICAL_TAXONOMY.items():
        for phrase in phrases:
            if re.search(r'\b' + re.escape(phrase) + r'\b', lower_text):
                derived.add(canonical)
                break

    # Validate supplied topics against known canonical taxonomy
    valid_supplied = {t for t in supplied_topics if t in CANONICAL_TAXONOMY}
    
    canonical_topics = sorted(list(valid_supplied.union(derived)))
    derived_topics = sorted(list(derived))
    
    return canonical_topics, derived_topics

