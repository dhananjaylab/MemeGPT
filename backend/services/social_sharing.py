"""
Social Media Sharing Optimization
Generates optimized metadata for social sharing
"""
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from urllib.parse import quote

logger = logging.getLogger(__name__)


@dataclass
class OpenGraphMetadata:
    """Open Graph metadata for social sharing"""
    title: str
    description: str
    image: str
    url: str
    type: str = "website"
    image_width: int = 1200
    image_height: int = 630
    site_name: str = "MemeGPT"
    
    def to_meta_tags(self) -> str:
        """Convert to HTML meta tags"""
        tags = f"""
        <meta property="og:title" content="{self._escape_html(self.title)}" />
        <meta property="og:description" content="{self._escape_html(self.description)}" />
        <meta property="og:image" content="{self.image}" />
        <meta property="og:image:width" content="{self.image_width}" />
        <meta property="og:image:height" content="{self.image_height}" />
        <meta property="og:url" content="{self.url}" />
        <meta property="og:type" content="{self.type}" />
        <meta property="og:site_name" content="{self.site_name}" />
        """
        return tags.strip()
    
    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters"""
        replacements = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#x27;",
        }
        for char, escape in replacements.items():
            text = text.replace(char, escape)
        return text


@dataclass
class TwitterCardMetadata:
    """Twitter Card metadata"""
    card_type: str = "summary_large_image"  # summary, summary_large_image, player, app
    title: str = ""
    description: str = ""
    image: str = ""
    site: str = "@memegpt"
    creator: str = "@memegpt"
    
    def to_meta_tags(self) -> str:
        """Convert to HTML meta tags"""
        tags = f"""
        <meta name="twitter:card" content="{self.card_type}" />
        <meta name="twitter:title" content="{self._escape_html(self.title)}" />
        <meta name="twitter:description" content="{self._escape_html(self.description)}" />
        <meta name="twitter:image" content="{self.image}" />
        <meta name="twitter:site" content="{self.site}" />
        <meta name="twitter:creator" content="{self.creator}" />
        """
        return tags.strip()
    
    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters"""
        replacements = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
        }
        for char, escape in replacements.items():
            text = text.replace(char, escape)
        return text


class SocialSharingOptimizer:
    """Optimizes content for social media sharing"""
    
    def __init__(self, base_url: str = "https://memegpt.com"):
        self.base_url = base_url.rstrip("/")
    
    def generate_meme_sharing_metadata(
        self,
        meme_id: str,
        title: str,
        description: str,
        image_url: str,
        creator: Optional[str] = None,
    ) -> Dict:
        """Generate sharing metadata for a meme"""
        
        # Truncate title and description for social platforms
        og_title = self._truncate(title, 60)
        og_description = self._truncate(description, 160)
        twitter_title = self._truncate(title, 70)
        twitter_description = self._truncate(description, 200)
        
        meme_url = f"{self.base_url}/meme/{meme_id}"
        
        og = OpenGraphMetadata(
            title=og_title,
            description=og_description,
            image=image_url,
            url=meme_url,
            type="image",
        )
        
        twitter = TwitterCardMetadata(
            card_type="summary_large_image",
            title=twitter_title,
            description=twitter_description,
            image=image_url,
            creator=creator or "@memegpt",
        )
        
        return {
            "meme_id": meme_id,
            "share_url": meme_url,
            "og": og,
            "twitter": twitter,
            "sharing_links": self._generate_sharing_links(meme_url, og_title),
        }
    
    def generate_page_sharing_metadata(
        self,
        page_type: str,  # gallery, trending, profile, etc.
        title: str,
        description: str,
        image_url: Optional[str] = None,
        page_id: Optional[str] = None,
    ) -> Dict:
        """Generate sharing metadata for pages"""
        
        og_title = self._truncate(title, 60)
        og_description = self._truncate(description, 160)
        
        page_url = f"{self.base_url}/{page_type}"
        if page_id:
            page_url += f"/{page_id}"
        
        og = OpenGraphMetadata(
            title=og_title,
            description=og_description,
            image=image_url or f"{self.base_url}/og-image.jpg",
            url=page_url,
            type="website",
        )
        
        twitter = TwitterCardMetadata(
            title=self._truncate(title, 70),
            description=self._truncate(description, 200),
            image=image_url or f"{self.base_url}/og-image.jpg",
        )
        
        return {
            "page_type": page_type,
            "share_url": page_url,
            "og": og,
            "twitter": twitter,
            "sharing_links": self._generate_sharing_links(page_url, og_title),
        }
    
    def _generate_sharing_links(self, url: str, title: str) -> Dict:
        """Generate social sharing links"""
        encoded_url = quote(url)
        encoded_title = quote(title)
        
        return {
            "twitter": f"https://twitter.com/intent/tweet?url={encoded_url}&text={encoded_title}",
            "facebook": f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}",
            "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}",
            "reddit": f"https://reddit.com/submit?url={encoded_url}&title={encoded_title}",
            "pinterest": f"https://pinterest.com/pin/create/button/?url={encoded_url}&description={encoded_title}",
            "telegram": f"https://t.me/share/url?url={encoded_url}&text={encoded_title}",
            "whatsapp": f"https://wa.me/?text={encoded_title}%20{encoded_url}",
        }
    
    @staticmethod
    def _truncate(text: str, max_length: int) -> str:
        """Truncate text to max length"""
        if len(text) > max_length:
            return text[:max_length - 3] + "..."
        return text
    
    def get_share_image_recommendations(self) -> Dict:
        """Get recommendations for share images"""
        return {
            "optimal_size": "1200x630px",
            "minimum_size": "600x315px",
            "format": "JPG or PNG",
            "max_file_size": "5MB",
            "aspect_ratio": "1.91:1",
            "tips": [
                "Use high contrast colors for visibility",
                "Include text overlay for context",
                "Add your branding/watermark",
                "Test across platforms before publishing",
            ]
        }


class ShareTrackingPixel:
    """Tracks social sharing engagement"""
    
    def __init__(self):
        self.shares: Dict = {}
    
    async def track_share(
        self,
        meme_id: str,
        platform: str,
        user_id: Optional[str] = None,
    ) -> Dict:
        """Track share event"""
        share_key = f"{meme_id}:{platform}"
        
        if share_key not in self.shares:
            self.shares[share_key] = {
                "meme_id": meme_id,
                "platform": platform,
                "count": 0,
                "users": set(),
            }
        
        self.shares[share_key]["count"] += 1
        if user_id:
            self.shares[share_key]["users"].add(user_id)
        
        return {
            "tracked": True,
            "share_count": self.shares[share_key]["count"],
            "unique_users": len(self.shares[share_key]["users"]),
        }
    
    def get_share_statistics(self, meme_id: str) -> Dict:
        """Get sharing statistics for meme"""
        stats = {}
        total_shares = 0
        total_users = set()
        
        for key, data in self.shares.items():
            if data["meme_id"] == meme_id:
                stats[data["platform"]] = {
                    "count": data["count"],
                    "unique_users": len(data["users"]),
                }
                total_shares += data["count"]
                total_users.update(data["users"])
        
        return {
            "meme_id": meme_id,
            "total_shares": total_shares,
            "total_unique_users": len(total_users),
            "by_platform": stats,
        }
