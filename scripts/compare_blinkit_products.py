
import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
CSV_FILE = PROJECT_DIR / "config" / "shopping_list.csv"
EXTRACTION_FILE = PROJECT_DIR / "output" / "blinkit_extraction_test.txt"
REPORT_FILE = PROJECT_DIR / "output" / "blinkit_comparison.txt"


def read_extraction_file(path):
    """Read the PAD extraction file, handling common Windows encodings."""
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeError:
            continue

    raise ValueError("Could not decode the extraction file.")


def normalize_size(size):
    """Normalize package sizes such as 1 L, 1 ltr, and 400 g."""
    size = size.lower().replace(" ", "")
    size = size.replace("ltr", "l")
    return size


def identify_category(name):
    name_lower = name.lower()

    # Check yogurt first to avoid "Milky Mist" being categorized as milk
    if any(word in name_lower for word in ("yogurt", "yoghurt", "doi")):
        return "yogurt"

    if "bread" in name_lower or "loaf" in name_lower:
        return "bread"

    # Check for milk but avoid false positives like "milky"
    if "milk" in name_lower and "milky" not in name_lower:
        return "milk"

    return "other"


def parse_products(raw_text):
    """Parse product cards ending with ADD in PAD's extracted text."""
    products = []
    # Split on ADD (not \bADD\b because ₹ is a word char and breaks the boundary)
    chunks = re.split(r"ADD", raw_text, flags=re.IGNORECASE)

    for chunk in chunks:
        chunk = re.sub(r"\s+", " ", chunk).strip()

        if not chunk:
            continue

        # Extract all prices - pick the first (current/discounted) price
        prices = re.findall(
            r"₹\s*([\d,]+(?:\.\d{1,2})?)",
            chunk
        )

        if not prices:
            continue

        try:
            # The first price is the displayed current/discounted price.
            price = Decimal(prices[0].replace(",", ""))
        except InvalidOperation:
            continue

        # Remove displayed prices from the product description.
        name = re.sub(
            r"₹\s*[\d,]+(?:\.\d{1,2})?",
            "",
            chunk
        ).strip(" -|:")

        # Identify a package size at the end of the product description.
        size_match = re.search(
            r"(\d+(?:\.\d+)?\s*(?:x\s*\d+(?:\.\d+)?\s*)?"
            r"(?:ml|ltr|l|g|kg))\s*$",
            name,
            flags=re.IGNORECASE
        )

        package_size = ""
        product_name = name

        if size_match:
            package_size = normalize_size(size_match.group(1))
            product_name = name[:size_match.start()].strip(" -:")

        products.append({
            "name": product_name,
            "category": identify_category(product_name),
            "price": price,
            "package_size": package_size,
            "text": chunk,
        })

    return products


def load_shopping_list():
    with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def brand_matches(name, preferred_brand):
    if not preferred_brand:
        return True

    # Permit minor spelling differences such as Britania/Britannia.
    normalized_name = re.sub(r"[^a-z0-9]", "", name.lower())
    normalized_brand = re.sub(r"[^a-z0-9]", "", preferred_brand.lower())

    if normalized_brand in normalized_name:
        return True

    if normalized_brand == "britania" and "britannia" in normalized_name:
        return True

    return False


def compare_products(shopping_items, products):
    lines = []

    lines.append("BLINKIT PRODUCT COMPARISON")
    lines.append("=" * 60)
    lines.append(f"Products parsed: {len(products)}")
    lines.append("Prices are from extracted page text; verify on Blinkit.")
    lines.append("")

    for item in shopping_items:
        item_name = item["item_name"].strip()
        category = identify_category(item_name)
        preferred_brand = item.get("preferred_brand", "").strip()
        preferred_size = normalize_size(item.get("package_size", ""))
        max_price = Decimal(item["max_unit_price"])
        requested_quantity = item.get("requested_quantity", "1")
        unit = item.get("unit", "")

        candidates = [
            product for product in products
            if product["category"] == category
        ]

        brand_candidates = [
            product for product in candidates
            if brand_matches(product["name"], preferred_brand)
        ]

        size_candidates = [
            product for product in brand_candidates
            if preferred_size
            and product["package_size"] == preferred_size
        ]

        affordable_candidates = [
            product for product in size_candidates
            if product["price"] <= max_price
        ]

        # Price-limit violations: brand+size match but over budget
        price_violations = [
            product for product in size_candidates
            if product["price"] > max_price
        ]

        # Package-size mismatches: brand matches but different size
        size_mismatches = [
            product for product in brand_candidates
            if product["package_size"] != preferred_size
        ]

        # Other same-brand candidates (different package)
        other_brand_candidates = [
            product for product in brand_candidates
            if product not in size_candidates and product not in size_mismatches
        ]

        # Other brands with matching package size
        other_brand_size_match = [
            product for product in candidates
            if not brand_matches(product["name"], preferred_brand)
            and preferred_size
            and product["package_size"] == preferred_size
        ]

        lines.append(f"ITEM: {item_name}")
        lines.append(f"  Requested quantity: {requested_quantity} {unit}")
        lines.append(f"  Preferred brand: {preferred_brand or 'Any'}")
        lines.append(f"  Preferred package: {preferred_size or 'Any'}")
        lines.append(f"  Maximum price per pack: Rs. {max_price:.2f}")
        lines.append("")

        # 1. Exact matches
        if affordable_candidates:
            affordable_candidates.sort(key=lambda p: p["price"])
            lines.append("  EXACT MATCHES (brand + package + within budget):")
            for product in affordable_candidates[:3]:
                lines.append(
                    f"    - {product['name']} | {product['package_size']} "
                    f"| Rs. {product['price']:.2f}"
                )
            lines.append("")

        # 2. Price-limit violations
        if price_violations:
            price_violations.sort(key=lambda p: p["price"])
            lines.append("  PRICE-LIMIT VIOLATIONS (brand + package match, over budget):")
            for product in price_violations[:3]:
                lines.append(
                    f"    - {product['name']} | {product['package_size']} "
                    f"| Rs. {product['price']:.2f} (limit: Rs. {max_price:.2f})"
                )
            lines.append("")

        # 3. Package-size mismatches (same brand, different size)
        if size_mismatches:
            size_mismatches.sort(key=lambda p: p["price"])
            lines.append("  PACKAGE-SIZE MISMATCHES (brand matches, different package):")
            for product in size_mismatches[:5]:
                lines.append(
                    f"    - {product['name']} | {product['package_size']} "
                    f"| Rs. {product['price']:.2f}"
                )
            lines.append("")

        # 4. Reasonable alternatives: other brands with same package size
        if other_brand_size_match:
            other_brand_size_match.sort(key=lambda p: p["price"])
            lines.append("  ALTERNATIVE BRANDS (matching package size):")
            for product in other_brand_size_match[:5]:
                lines.append(
                    f"    - {product['name']} | {product['package_size']} "
                    f"| Rs. {product['price']:.2f}"
                )
            lines.append("")

        # 5. Other same-brand candidates (if any not already shown)
        if other_brand_candidates:
            other_brand_candidates.sort(key=lambda p: p["price"])
            lines.append("  OTHER SAME-BRAND OPTIONS:")
            for product in other_brand_candidates[:3]:
                lines.append(
                    f"    - {product['name']} | {product['package_size']} "
                    f"| Rs. {product['price']:.2f}"
                )
            lines.append("")

        # Summary if nothing found
        if not affordable_candidates and not price_violations and not size_mismatches and not other_brand_size_match and not other_brand_candidates:
            lines.append("  NO CANDIDATES FOUND for this item.")
            lines.append("")

        lines.append("-" * 60)

    lines.append("=" * 60)
    lines.append(
        "SAFETY: This script only compares extracted text. "
        "It does not add items, place an order, or initiate payment."
    )

    return "\n".join(lines)


def main():
    if not CSV_FILE.exists():
        raise FileNotFoundError(f"Shopping list not found: {CSV_FILE}")

    if not EXTRACTION_FILE.exists():
        raise FileNotFoundError(
            f"Blinkit extraction file not found: {EXTRACTION_FILE}"
        )

    raw_text = read_extraction_file(EXTRACTION_FILE)
    shopping_items = load_shopping_list()
    products = parse_products(raw_text)

    report = compare_products(shopping_items, products)

    print(report)
    REPORT_FILE.write_text(report, encoding="utf-8")

    print(f"\nSaved comparison report to: {REPORT_FILE}")


if __name__ == "__main__":
    main()
