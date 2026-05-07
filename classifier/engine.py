import yaml
import re
from typing import List, Optional
from db.models import Source


class Classifier:
    def __init__(self, config_path: str):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.themes = self.config["themes"]

    def classify(self, post_text: str, post_title: Optional[str], source: Source) -> List[str]:
        if source.theme_override:
            return [source.theme_override.name]

        full_text = (post_title or "") + " " + (post_text or "")
        full_text_lower = full_text.lower()
        matched_themes = []

        # Extract hashtags
        hashtags = re.findall(r"#(\w+)", full_text)

        for theme_name, theme_data in self.themes.items():
            keywords = theme_data.get("keywords", [])
            for kw in keywords:
                if kw.lower() in full_text_lower:
                    matched_themes.append(theme_name)
                    break
            # Also check hashtags
            for tag in hashtags:
                if tag.lower() == theme_name or any(kw in tag.lower() for kw in keywords):
                    matched_themes.append(theme_name)
                    break

        # Remove duplicates preserving order
        seen = set()
        unique = []
        for t in matched_themes:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        return unique