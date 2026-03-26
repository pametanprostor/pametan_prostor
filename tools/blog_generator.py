"""
Blog generator: calls Claude API with tool use, renders Jinja2 template,
saves blog post HTML, and injects a card into blog.html listing.
"""
import os
import re
import json
from datetime import date
from jinja2 import Environment, FileSystemLoader
import anthropic
from image_selector import select_image

SYSTEM_PROMPT = """Ti si stručni pisac za Pametan Prostor, radionicu za izradu nameštaja po meri iz Pančeva. Pišeš blog post za sajt pametanprostor.rs.

PRAVILA PISANJA:
- Piši iz perspektive Pametan Prostor tima, u prvom licu množine ("mi", "naš tim", "naša radionica")
- Ton je topao, profesionalan i pristupačan. Piši kao da savetujete prijatelja koji renovira stan
- Koristi "vi" formu kada se obraćaš čitaocima
- Piši prirodnim srpskim jezikom (ekavica), ne prevedenim sa engleskog
- Tehničke termine za materijale i okov (Blum, Hettich, MDF, iveral, kvarcopol, granit, Dektop) ostavi na originalnom jeziku
- Svaki post mora sadržati praktične savete koje čitalac može primeniti
- Uključi konkretne primere iz prakse gde je moguće (dimenzije, materijali, cene okvirno)
- Post treba da bude 800 do 1500 reči
- Kreiraj 3 do 5 FAQ pitanja sa odgovorima
- Svaki post završi pozivom na besplatnu konsultaciju

ZABRANJENO:
- NIKAKO ne koristi crtu (dash) ni dugu (—) ni kratku (–) ni srednju (-) kao interpunkciju u rečenicama
- Umesto crte koristi zarez, tačku i zarez, ili preformuliši rečenicu
- Opsege piši rečima: "od 14 do 21 radni dan", NE "14-21 radni dan"
- Ne koristi sledeće reči: delve, tapestry, vibrant, landscape, realm, embark, excels, vital, comprehensive, intricate, pivotal, moreover, arguably, notably, thrilled, robust, seamless, cutting-edge, state-of-the-art, unparalleled, game-changing, revolutionary, synergy, empower, unleash, future-proof, mission-critical, turnkey, streamlined, best-in-class, top-tier
- Ne koristi hrvatske reči ni izraze, samo srpski ekavica
- Ne pisati "ukoliko" već "ako"

KONTEKST PAMETAN PROSTOR:
- Izrađuje: kuhinje po meri, plakare i ugradne ormare, komadni nameštaj (TV komode, radne stolove, biblioteke)
- Premium materijali: Blum i Hettich okovi, kvarcopol, granit, Dektop ploče za radne površine
- CNC preciznost, ručna obrada detalja
- Proces: konsultacija → merenje → 3D projekat → izrada → montaža
- Besplatno merenje i konsultacija
- Pokriva: Pančevo, Beograd, Novi Sad
- Garancija 2 godine
- Telefon: 065 2262 308
- Sajt: pametanprostor.rs

SEO ZAHTEVI:
- Prirodno uključi ciljani keyword 3 do 5 puta
- H2 naslovi deskriptivni i sa relevantnim pojmovima
- Meta description: 150 do 160 karaktera
- Slug za URL u latinici, bez dijakritika, sa crticama

SRPSKI PRAVOPIS (obavezno):
- Uz brojeve 5 i više koristi genitiv množine
- "nijedan/nijedna/nijedno" piši kao jednu reč
- Gramatičko slaganje roda, broja i padeža
- Zarez pre "koji/koja/što" u zavisnoj rečenici

FORMAT body_html:
- Koristiti HTML tagove: <h2>, <h3>, <p>, <ul>, <li>, <strong>
- NE dodavati <html>, <body>, <head> ni CSS stilove
- Poslednji paragraf treba da bude CTA koji pominje besplatnu konsultaciju na 065 2262 308
"""

BLOG_TOOL = {
    "name": "create_blog_post",
    "description": "Kreira blog post sa svim potrebnim poljima",
    "input_schema": {
        "type": "object",
        "properties": {
            "slug": {"type": "string", "description": "URL slug u latinici bez dijakritika, sa crticama"},
            "title": {"type": "string", "description": "Naslov blog posta"},
            "meta_title": {"type": "string", "description": "SEO meta title, max 65 karaktera"},
            "meta_description": {"type": "string", "description": "SEO meta description, 150-160 karaktera"},
            "excerpt": {"type": "string", "description": "Kratki izvod za karticu u listingu, max 120 karaktera"},
            "category": {
                "type": "string",
                "enum": ["Kuhinje", "Plakari i ormari", "Komadni nameštaj", "Enterijer saveti", "Renoviranje", "Materijali"]
            },
            "category_slug": {
                "type": "string",
                "enum": ["kuhinje", "plakari", "komadni-namestaj", "enterijer", "renoviranje", "materijali"]
            },
            "reading_time": {"type": "integer", "description": "Procenjeno vreme čitanja u minutima"},
            "body_html": {"type": "string", "description": "Ceo sadržaj posta kao HTML (h2, h3, p, ul, li, strong)"},
            "faq": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"}
                    },
                    "required": ["question", "answer"]
                }
            },
            "instagram_caption": {
                "type": "string",
                "description": "Instagram caption za objavu. Max 2200 karaktera. Uključi relevantne hashtage na kraju."
            },
            "carousel_slides": {
                "type": "array",
                "description": "Slajdovi za Instagram carousel (5-8 slajdova)",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["cover", "text", "photo", "cta"]},
                        "headline": {"type": "string", "description": "Glavni naslov slajda, max 60 karaktera"},
                        "subtitle": {"type": "string", "description": "Podnaslov ili uvod, max 100 karaktera"},
                        "body": {"type": "string", "description": "Tekst slajda, max 200 karaktera"},
                        "tip_number": {"type": "integer", "description": "Broj saveta (za text tip slajdove)"}
                    },
                    "required": ["type", "headline"]
                }
            }
        },
        "required": [
            "slug", "title", "meta_title", "meta_description", "excerpt",
            "category", "category_slug", "reading_time", "body_html",
            "faq", "instagram_caption", "carousel_slides"
        ]
    }
}


class BlogGenerator:
    def __init__(self, config: dict):
        self.config = config
        self.client = anthropic.Anthropic()
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.jinja = Environment(loader=FileSystemLoader(template_dir), autoescape=False)

    def generate(self, topic: str) -> dict:
        """Call Claude with tool use and return the structured blog post data."""
        print(f"Generišem blog post za temu: '{topic}' ...")

        response = self.client.messages.create(
            model=self.config["claude"]["model"],
            max_tokens=self.config["claude"]["max_tokens"],
            system=SYSTEM_PROMPT,
            tools=[BLOG_TOOL],
            tool_choice={"type": "tool", "name": "create_blog_post"},
            messages=[
                {
                    "role": "user",
                    "content": f"Napiši blog post na temu: {topic}"
                }
            ]
        )

        # Extract tool use result
        for block in response.content:
            if block.type == "tool_use" and block.name == "create_blog_post":
                data = block.input
                # Add metadata
                data["published_date"] = date.today().isoformat()
                data["published_date_display"] = date.today().strftime("%d.%m.%Y.")
                data["hero_image"] = select_image(data["category_slug"], self.config)
                return data

        raise RuntimeError("Claude nije vratio tool_use blok. Pokušajte ponovo.")

    def save_blog_post(self, data: dict) -> str:
        """Render and save the blog post HTML. Returns path to saved file."""
        template = self.jinja.get_template("blog_post.html")
        html = template.render(**data)

        blog_dir = os.path.join(os.path.dirname(__file__), self.config["paths"]["blog"])
        os.makedirs(blog_dir, exist_ok=True)

        output_path = os.path.join(blog_dir, f"{data['slug']}.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"  Blog post sačuvan: blog/{data['slug']}.html")
        return output_path

    def update_blog_listing(self, data: dict):
        """Inject a new card into blog.html between the marker comments."""
        blog_html_path = os.path.join(os.path.dirname(__file__), "..", "blog.html")

        with open(blog_html_path, "r", encoding="utf-8") as f:
            content = f.read()

        card_html = self._render_card(data)

        # Inject AFTER <!-- BLOG_CARDS_START -->
        marker = "<!-- BLOG_CARDS_START -->"
        if marker not in content:
            print("  UPOZORENJE: Marker <!-- BLOG_CARDS_START --> nije pronađen u blog.html")
            return

        content = content.replace(marker, f"{marker}\n{card_html}")

        with open(blog_html_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"  Kartica dodata u blog.html listing")

    def _render_card(self, data: dict) -> str:
        """Generate the HTML for a single blog card."""
        excerpt = data.get("excerpt", data.get("meta_description", "")[:120])
        return f'''          <article class="blog-card rounded-xl overflow-hidden bg-zinc-900 group" role="listitem" data-category="{data['category_slug']}">
            <a href="/blog/{data['slug']}.html" class="block">
              <div class="aspect-[16/9] overflow-hidden">
                <img src="{data['hero_image']}" alt="{data['title']}"
                     class="w-full h-full object-cover opacity-80 group-hover:scale-105 group-hover:opacity-95 transition-all duration-500"
                     loading="lazy" width="600" height="338"/>
              </div>
              <div class="p-6">
                <div class="flex items-center gap-3 mb-3">
                  <span class="text-xs text-gold-400 font-medium tracking-wider uppercase">{data['category']}</span>
                  <span class="text-zinc-600 text-xs">·</span>
                  <span class="text-zinc-500 text-xs">{data['reading_time']} min čitanja</span>
                </div>
                <h2 class="font-serif text-lg font-semibold text-white mb-2 group-hover:text-gold-400 transition-colors leading-snug">{data['title']}</h2>
                <p class="text-zinc-500 text-sm leading-relaxed mb-4">{excerpt}</p>
                <span class="text-gold-500 text-sm font-medium flex items-center gap-1.5">
                  Pročitajte
                  <svg class="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/></svg>
                </span>
              </div>
            </a>
          </article>'''
