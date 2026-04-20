"""
Sitemap Generation Service
Generates sitemap.xml and robots.txt for SEO
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ChangeFrequency(str, Enum):
    """Change frequency for sitemap"""
    ALWAYS = "always"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    NEVER = "never"


class SitemapEntry:
    """Single sitemap entry"""
    
    def __init__(
        self,
        loc: str,
        lastmod: Optional[datetime] = None,
        changefreq: ChangeFrequency = ChangeFrequency.WEEKLY,
        priority: float = 0.5,
        images: Optional[List[str]] = None,
    ):
        self.loc = loc
        self.lastmod = lastmod or datetime.utcnow()
        self.changefreq = changefreq
        self.priority = max(0.0, min(1.0, priority))  # Clamp to [0, 1]
        self.images = images or []
    
    def to_xml(self) -> str:
        """Convert to XML entry"""
        xml = f"  <url>\n"
        xml += f"    <loc>{self._escape_xml(self.loc)}</loc>\n"
        xml += f"    <lastmod>{self.lastmod.isoformat()}</lastmod>\n"
        xml += f"    <changefreq>{self.changefreq.value}</changefreq>\n"
        xml += f"    <priority>{self.priority}</priority>\n"
        
        # Add images if present
        for image_url in self.images:
            xml += f"    <image:image>\n"
            xml += f"      <image:loc>{self._escape_xml(image_url)}</image:loc>\n"
            xml += f"    </image:image>\n"
        
        xml += f"  </url>\n"
        return xml
    
    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape XML special characters"""
        replacements = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&apos;",
        }
        for char, escape in replacements.items():
            text = text.replace(char, escape)
        return text


class SitemapGenerator:
    """Generates XML sitemaps"""
    
    def __init__(self, base_url: str = "https://memegpt.com"):
        self.base_url = base_url.rstrip("/")
        self.entries: List[SitemapEntry] = []
    
    def add_url(
        self,
        path: str,
        changefreq: ChangeFrequency = ChangeFrequency.WEEKLY,
        priority: float = 0.5,
        lastmod: Optional[datetime] = None,
        images: Optional[List[str]] = None,
    ) -> None:
        """Add URL to sitemap"""
        url = f"{self.base_url}{path}"
        entry = SitemapEntry(
            loc=url,
            lastmod=lastmod,
            changefreq=changefreq,
            priority=priority,
            images=images,
        )
        self.entries.append(entry)
    
    def generate_static_urls(self) -> None:
        """Add static pages to sitemap"""
        static_pages = [
            ("/", ChangeFrequency.WEEKLY, 1.0),
            ("/gallery", ChangeFrequency.HOURLY, 0.9),
            ("/trending", ChangeFrequency.DAILY, 0.8),
            ("/templates", ChangeFrequency.WEEKLY, 0.8),
            ("/about", ChangeFrequency.MONTHLY, 0.5),
            ("/contact", ChangeFrequency.MONTHLY, 0.5),
            ("/privacy", ChangeFrequency.YEARLY, 0.3),
            ("/terms", ChangeFrequency.YEARLY, 0.3),
        ]
        
        for path, freq, priority in static_pages:
            self.add_url(path, changefreq=freq, priority=priority)
    
    async def add_dynamic_urls(
        self,
        templates: List[Dict],
        trending_memes: List[Dict],
        categories: List[str],
    ) -> None:
        """Add dynamic URLs"""
        # Add template URLs
        for template in templates:
            self.add_url(
                f"/template/{template['id']}",
                changefreq=ChangeFrequency.WEEKLY,
                priority=0.7,
                images=[template.get("thumbnail_url")],
            )
        
        # Add trending meme URLs
        for meme in trending_memes:
            self.add_url(
                f"/meme/{meme['id']}",
                changefreq=ChangeFrequency.DAILY,
                priority=0.8,
                lastmod=datetime.fromisoformat(meme.get("created_at", "2024-01-01")),
                images=[meme.get("image_url")],
            )
        
        # Add category URLs
        for category in categories:
            self.add_url(
                f"/category/{category}",
                changefreq=ChangeFrequency.WEEKLY,
                priority=0.6,
            )
    
    def generate_xml(self) -> str:
        """Generate sitemap XML"""
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        xml += '         xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        
        for entry in self.entries:
            xml += entry.to_xml()
        
        xml += '</urlset>'
        return xml
    
    def generate_sitemap_index(self, sitemaps: List[Dict]) -> str:
        """Generate sitemap index for large sites"""
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        for sitemap in sitemaps:
            xml += f'  <sitemap>\n'
            xml += f'    <loc>{sitemap["url"]}</loc>\n'
            if "lastmod" in sitemap:
                xml += f'    <lastmod>{sitemap["lastmod"]}</lastmod>\n'
            xml += f'  </sitemap>\n'
        
        xml += '</sitemapindex>'
        return xml


class RobotsGenerator:
    """Generates robots.txt"""
    
    def __init__(self, base_url: str = "https://memegpt.com"):
        self.base_url = base_url.rstrip("/")
        self.rules: List[Dict] = []
        self.sitemaps: List[str] = []
    
    def add_rule(
        self,
        user_agent: str = "*",
        allow: Optional[List[str]] = None,
        disallow: Optional[List[str]] = None,
        crawl_delay: Optional[float] = None,
    ) -> None:
        """Add robot exclusion rule"""
        rule = {
            "user_agent": user_agent,
            "allow": allow or [],
            "disallow": disallow or [],
            "crawl_delay": crawl_delay,
        }
        self.rules.append(rule)
    
    def add_sitemap(self, path: str) -> None:
        """Add sitemap URL"""
        url = f"{self.base_url}{path}" if path.startswith("/") else path
        self.sitemaps.append(url)
    
    def generate_default_rules(self) -> None:
        """Generate standard robots.txt rules"""
        # Allow crawlers
        self.add_rule(
            user_agent="*",
            allow=["/", "/gallery", "/trending", "/template", "/meme"],
            disallow=["/admin", "/api", "/user/private"],
            crawl_delay=1.0,
        )
        
        # Block bad bots
        self.add_rule(
            user_agent="MJ12bot",
            disallow=["/"],
        )
        
        self.add_rule(
            user_agent="AhrefsBot",
            disallow=["/"],
        )
    
    def generate_text(self) -> str:
        """Generate robots.txt content"""
        lines = []
        
        for rule in self.rules:
            lines.append(f"User-agent: {rule['user_agent']}")
            
            for allow_path in rule["allow"]:
                lines.append(f"Allow: {allow_path}")
            
            for disallow_path in rule["disallow"]:
                lines.append(f"Disallow: {disallow_path}")
            
            if rule["crawl_delay"]:
                lines.append(f"Crawl-delay: {rule['crawl_delay']}")
            
            lines.append("")
        
        # Add sitemaps
        for sitemap in self.sitemaps:
            lines.append(f"Sitemap: {sitemap}")
        
        return "\n".join(lines)


# SEO optimization helpers
class SEOOptimizer:
    """SEO optimization utilities"""
    
    @staticmethod
    def generate_canonical_url(base_url: str, path: str) -> str:
        """Generate canonical URL"""
        base = base_url.rstrip("/")
        path = path.lstrip("/")
        return f"{base}/{path}"
    
    @staticmethod
    def get_meta_tags_for_page(
        title: str,
        description: str,
        keywords: Optional[List[str]] = None,
        canonical_url: Optional[str] = None,
    ) -> str:
        """Generate HTML meta tags"""
        tags = f'<title>{title}</title>\n'
        tags += f'<meta name="description" content="{description}" />\n'
        
        if keywords:
            tags += f'<meta name="keywords" content="{", ".join(keywords)}" />\n'
        
        if canonical_url:
            tags += f'<link rel="canonical" href="{canonical_url}" />\n'
        
        # Additional SEO meta tags
        tags += '<meta charset="utf-8" />\n'
        tags += '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        tags += '<meta name="language" content="en" />\n'
        
        return tags
    
    @staticmethod
    def generate_structured_data(schema_type: str, data: Dict) -> str:
        """Generate JSON-LD structured data"""
        import json
        
        schema = {
            "@context": "https://schema.org",
            "@type": schema_type,
            **data,
        }
        
        return f'<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>'
