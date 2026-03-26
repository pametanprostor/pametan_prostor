#!/usr/bin/env python3
"""
Pametan Prostor – Blog & Instagram Carousel Generator

Upotreba:
  python tools/generate.py --topic "kako odabrati radnu površinu za kuhinju po meri"
  python tools/generate.py --topic "..." --blog-only
  python tools/generate.py --topic "..." --carousel-only

Zahteva:
  pip install -r tools/requirements.txt
  export ANTHROPIC_API_KEY="sk-ant-..."
"""
import argparse
import os
import sys

# Allow importing sibling modules
sys.path.insert(0, os.path.dirname(__file__))

import yaml
from blog_generator import BlogGenerator
from carousel_generator import CarouselGenerator


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_first_run(config: dict):
    """Print warning if blog infrastructure doesn't exist yet."""
    blog_html = os.path.join(os.path.dirname(__file__), "..", "blog.html")
    blog_dir = os.path.join(os.path.dirname(__file__), "..", "blog")
    missing = []
    if not os.path.exists(blog_html):
        missing.append("blog.html")
    if not os.path.exists(blog_dir):
        missing.append("blog/")
    if missing:
        print(f"\nNAPOMENA: Sledeći fajlovi nedostaju: {', '.join(missing)}")
        print("Kreirajte ih pre pokretanja generatora.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Pametan Prostor blog & carousel generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Primeri:
  python tools/generate.py --topic "kako odabrati radnu površinu za kuhinju"
  python tools/generate.py --topic "plakari po meri prednosti" --blog-only
  python tools/generate.py --topic "enterijer saveti" --carousel-only
        """
    )
    parser.add_argument("--topic", required=True, help="Tema blog posta")
    parser.add_argument("--blog-only", action="store_true", help="Generiši samo blog post, bez carousela")
    parser.add_argument("--carousel-only", action="store_true", help="Generiši samo carousel, bez blog posta")
    args = parser.parse_args()

    if "ANTHROPIC_API_KEY" not in os.environ:
        print("GREŠKA: Postavi ANTHROPIC_API_KEY environment varijablu.")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    config = load_config()
    check_first_run(config)

    blog_gen = BlogGenerator(config)

    print(f"\n{'='*60}")
    print(f"Tema: {args.topic}")
    print(f"{'='*60}")

    # Generate content via Claude API
    data = blog_gen.generate(args.topic)
    print(f"\nGenerisano:")
    print(f"  Naslov:   {data['title']}")
    print(f"  Kategorija: {data['category']}")
    print(f"  Slug:     {data['slug']}")
    print(f"  Čitanje:  {data['reading_time']} min")
    print(f"  Slika:    {data['hero_image']}")
    print()

    if not args.carousel_only:
        blog_gen.save_blog_post(data)
        blog_gen.update_blog_listing(data)

    if not args.blog_only:
        carousel_gen = CarouselGenerator(config)
        carousel_gen.generate(data)

    print(f"\n{'='*60}")
    print("Gotovo!")
    if not args.carousel_only:
        print(f"  Blog post: blog/{data['slug']}.html")
        print(f"  Listing:   blog.html (kartica dodata)")
    if not args.blog_only:
        print(f"  Carousel:  tools/output/carousels/{data['slug']}/slides.html")
        print(f"  Caption:   tools/output/carousels/{data['slug']}/caption.txt")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
