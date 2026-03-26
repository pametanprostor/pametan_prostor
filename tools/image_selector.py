"""
Selects the best local image for a blog post based on category keyword matching.
"""
import os


def select_image(category_slug: str, config: dict) -> str:
    """
    Returns a root-relative image path like /images/kuhinja-bela-ostrvo.webp
    Falls back to hero.webp if nothing matches.
    """
    images_dir = os.path.join(os.path.dirname(__file__), config["paths"]["images"])
    keywords = config.get("image_category_map", {}).get(category_slug, [])

    try:
        all_files = [f for f in os.listdir(images_dir) if f.lower().endswith((".webp", ".jpg", ".jpeg", ".png"))]
        # Prefer .webp: sort so .webp files come first
        available = sorted(all_files, key=lambda f: (0 if f.lower().endswith(".webp") else 1))
    except FileNotFoundError:
        return "/images/hero.webp"

    # Try to find a match by keyword (prefer webp)
    for keyword in keywords:
        for filename in available:
            if keyword.lower() in filename.lower():
                return f"/images/{filename}"

    # Fallback: any portfolio image
    portfolio_images = [f for f in available if f.startswith("portfolio-")]
    if portfolio_images:
        return f"/images/{portfolio_images[0]}"

    return "/images/hero.webp"
