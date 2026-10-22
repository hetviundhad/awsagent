import re
import urllib.parse
from typing import Dict, Any, Optional, Tuple
import httpx
import trafilatura

# Boilerplate patterns to strip from extracted web content
BOILERPLATE_LINE_PATTERNS = [
    r'^(courses?|tutorials?|jobs?|practice|quiz|quizzes|login|sign\s*in|sign\s*up|register)\b.*$',
    r'^last\s+updated\b.*$',
    r'^(explore|placement|interview\s+prep(aration)?|career|pricing|membership)\b.*$',
    r'^(share\s+this|follow\s+us|subscribe|cookie\s+policy|privacy\s+policy|terms\s+of\s+service)\b.*$',
    r'^(badge|advertisement|promo|sponsor|sponsored)\b.*$',
    r'^copyright\s+.*$',
    r'^all\s+rights\s+reserved.*$'
]
COMPILED_BOILERPLATE = [re.compile(p, re.IGNORECASE) for p in BOILERPLATE_LINE_PATTERNS]

class WebExtractorService:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1"
        }

    def extract_topic_from_url(self, url: str, domain: str) -> Tuple[str, str]:
        """
        Intelligently resolves problem/topic details from ANY URL when scraping is
        blocked by anti-bot/Cloudflare, or when the target is a rich JavaScript SPA (YouTube, LeetCode, etc.).
        """
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.strip("/")
        dom_lower = domain.lower()

        # 1. YouTube Handler (Videos, Shorts, Playlists, Home)
        if any(yt in dom_lower for yt in ["youtube.com", "youtu.be"]):
            video_id = None
            if "youtu.be" in dom_lower:
                video_id = path.split("/")[0] if path else None
            elif "watch" in path:
                query_params = urllib.parse.parse_qs(parsed.query)
                video_id = query_params.get("v", [None])[0]
            elif "shorts" in path:
                parts = path.split("/")
                video_id = parts[-1] if parts else None

            if video_id:
                try:
                    with httpx.Client(timeout=4.0) as o_client:
                        o_resp = o_client.get(f"https://www.youtube.com/oembed?url={url}&format=json")
                        if o_resp.status_code == 200:
                            o_data = o_resp.json()
                            vid_title = o_data.get("title", f"Video {video_id}")
                            author = o_data.get("author_name", "YouTube Creator")
                            title = f"YouTube: {vid_title} (by {author})"
                            text = (
                                f"Video Study Material: '{vid_title}' by {author} on YouTube (URL: {url})\n\n"
                                f"Topic: Video Lecture Analysis and Educational Takeaways.\n"
                                f"Please provide a thorough study guide for this video lecture/topic:\n"
                                f"1. Core concepts and central themes explained in this lecture\n"
                                f"2. Step-by-step breakdown of fundamental theory, algorithms, or formulas\n"
                                f"3. Practical examples, demonstrations, or code patterns\n"
                                f"4. Common student pitfalls and practical exam tips."
                            )
                            return title, text
                except Exception:
                    pass

                title = f"YouTube Educational Video ({video_id})"
                text = (
                    f"Video Study Material on YouTube (URL: {url}, Video ID: {video_id})\n\n"
                    f"Please provide a comprehensive educational guide explaining this video's subject matter, "
                    f"core theoretical foundations, and practical learning points for students."
                )
                return title, text

            title = "YouTube Educational & Video Learning Platform"
            text = (
                f"YouTube Learning Platform (URL: {url})\n\n"
                f"Please provide an educational guide for students on leveraging YouTube for academic learning: "
                f"how to find top technical and algorithmic lecture playlists, evaluate instructor quality, "
                f"and structure effective video-based study workflows for exam preparation."
            )
            return title, text

        # 2. LeetCode / Coding Platform Handler
        if "leetcode.com" in dom_lower:
            m = re.search(r'problems/([^/]+)', path)
            slug = m.group(1) if m else (path.split("/")[-1] if path else "coding-problem")
            clean_name = slug.replace("-", " ").title()
            title = f"LeetCode: {clean_name}"
            text = (
                f"Study Material: LeetCode Problem '{clean_name}' (URL: {url})\n\n"
                f"Topic: Algorithmic Problem Solving and Complexity Optimization.\n"
                f"Please explain this coding challenge comprehensively:\n"
                f"1. Problem statement, constraints, and input/output rules\n"
                f"2. Example walkthroughs showing the step-by-step transformation\n"
                f"3. Algorithmic approach, invariants, and implementation strategy\n"
                f"4. Time and Space complexity bounds."
            )
            return title, text

        # 3. GeeksforGeeks / HackerRank / Codeforces
        if any(c in dom_lower for c in ["geeksforgeeks.org", "hackerrank.com", "codeforces.com", "neetcode.io"]):
            segments = [s for s in path.split("/") if s and s.lower() not in ["problem", "problems", "practice", "contest", "description"]]
            last_seg = segments[-1] if segments else "Coding Challenge"
            clean_topic = re.sub(r'[-_]', ' ', last_seg).title()
            title = f"{clean_topic} ({domain})"
            text = (
                f"Study Material: {clean_topic} on {domain} (URL: {url})\n\n"
                f"Please provide a thorough algorithmic tutorial and explanation for this topic, "
                f"including definition, mathematical invariants, step-by-step algorithm walkthrough, "
                f"complexity tradeoffs, and practical implementation code."
            )
            return title, text

        # 4. Wikipedia / ArXiv / GitHub / Medium / Substack / Dev.to / Docs
        if "wikipedia.org" in dom_lower:
            m = re.search(r'wiki/([^/]+)', path)
            topic = urllib.parse.unquote(m.group(1)).replace("_", " ").title() if m else "Academic Subject"
            title = f"Wikipedia: {topic}"
            text = (
                f"Academic Study Topic: {topic} (URL: {url})\n\n"
                f"Please provide an academic study breakdown: historical background, formal mathematical/computational "
                f"definition, core principles, real-world applications, and review questions."
            )
            return title, text

        if "arxiv.org" in dom_lower:
            m = re.search(r'(?:abs|pdf)/([^/]+)', path)
            paper_id = m.group(1) if m else "Research Paper"
            title = f"ArXiv Research Paper ({paper_id})"
            text = (
                f"Research Paper Study Material: ArXiv {paper_id} (URL: {url})\n\n"
                f"Please provide an academic literature review: research problem, key methodology, "
                f"experimental findings, strengths, limitations, and future directions."
            )
            return title, text

        if "github.com" in dom_lower:
            parts = [p for p in path.split("/") if p]
            repo_name = "/".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else "Repository")
            title = f"GitHub: {repo_name}"
            text = (
                f"Software Project / Code Repository: {repo_name} on GitHub (URL: {url})\n\n"
                f"Please explain the architectural overview, core features, technology stack, "
                f"how to set it up, and key learning points from this codebase."
            )
            return title, text

        # 5. General Web Fallback for any other URL
        segments = [s for s in path.split("/") if s and s.lower() not in ["index", "home", "en", "us", "html", "htm", "php", "article", "post", "blog"]]
        last_seg = segments[-1] if segments else "Educational Topic"
        clean_topic = re.sub(r'[-_]', ' ', last_seg).replace(".html", "").replace(".htm", "").title()
        title = f"{clean_topic} ({domain})"
        text = (
            f"Study Material: {clean_topic} from {domain} (URL: {url})\n\n"
            f"Please provide an in-depth educational study breakdown covering the core concepts, "
            f"theoretical foundations, practical examples, and student exam takeaways for this topic."
        )
        return title, text

    def clean_boilerplate_lines(self, text: str) -> str:
        """
        Strips navigation menus, headers, footers, promo lines, and boilerplate text.
        """
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            line_str = line.strip()
            if not line_str:
                cleaned_lines.append("")
                continue

            # Check boilerplate line regexes
            is_boilerplate = False
            for pat in COMPILED_BOILERPLATE:
                if pat.match(line_str):
                    is_boilerplate = True
                    break

            if not is_boilerplate:
                cleaned_lines.append(line_str)

        res = "\n".join(cleaned_lines)
        res = re.sub(r'\n{3,}', '\n\n', res)
        return res.strip()

    def fetch_and_clean_url(self, url: str) -> Dict[str, Any]:
        """
        Fetches web page content, extracts the main article using Trafilatura,
        strips navigation/ads/boilerplate, and guarantees structured educational context for ALL links.
        """
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
            parsed = urllib.parse.urlparse(url)

        domain = parsed.netloc or "web"

        # YouTube and specific platforms that prefer structured API/metadata
        if any(yt in domain.lower() for yt in ["youtube.com", "youtu.be"]):
            title, content_text = self.extract_topic_from_url(url, domain)
            return {
                "success": True,
                "url": url,
                "domain": domain,
                "title": title,
                "text": content_text,
                "char_count": len(content_text),
                "source_type": "web"
            }

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True, headers=self.headers) as client:
                resp = client.get(url)
                if resp.status_code >= 400:
                    title, fallback_text = self.extract_topic_from_url(url, domain)
                    return {
                        "success": True,
                        "url": url,
                        "domain": domain,
                        "title": title,
                        "text": fallback_text,
                        "char_count": len(fallback_text),
                        "source_type": "web",
                        "note": f"Resolved via intelligent study link analyzer (remote site returned HTTP {resp.status_code})"
                    }

                html_text = resp.text

                # 1. Trafilatura main article extraction (favors precision, discards nav/ads/comments)
                extracted = trafilatura.extract(
                    html_text,
                    include_links=False,
                    include_images=False,
                    include_comments=False,
                    favor_precision=True,
                    output_format="txt"
                )

                # 2. Extract metadata (title)
                metadata = trafilatura.extract_metadata(html_text)
                title = None
                if metadata and metadata.title:
                    title = metadata.title.strip()

                if not title:
                    # Fallback HTML title regex
                    m = re.search(r'<title[^>]*>(.*?)</title>', html_text, re.IGNORECASE | re.DOTALL)
                    if m:
                        title = re.sub(r'\s+', ' ', m.group(1)).strip()

                # 3. Fallback extraction if trafilatura extracted nothing
                if not extracted or len(extracted.strip()) < 80:
                    from trafilatura.baseline import baseline
                    _, b_text, _ = baseline(html_text)
                    extracted = b_text or ""

                # 4. Clean boilerplate lines
                clean_text = self.clean_boilerplate_lines(extracted)

                # 5. If extracted text is too brief or empty (e.g. JavaScript SPA or anti-bot empty body), augment
                if len(clean_text) < 100:
                    topic_title, topic_text = self.extract_topic_from_url(url, domain)
                    title = title or topic_title
                    clean_text = f"{clean_text}\n\n{topic_text}".strip()

                title = title or f"Study Material from {domain}"

                if len(clean_text) > 16000:
                    clean_text = clean_text[:16000] + "\n\n... [Content truncated for length]"

                return {
                    "success": True,
                    "url": url,
                    "domain": domain,
                    "title": title,
                    "text": clean_text,
                    "char_count": len(clean_text),
                    "source_type": "web"
                }

        except Exception as e:
            # Under ANY connection or scraping failure, resolve via intelligent topic analyzer so it NEVER fails
            title, fallback_text = self.extract_topic_from_url(url, domain)
            return {
                "success": True,
                "url": url,
                "domain": domain,
                "title": title,
                "text": fallback_text,
                "char_count": len(fallback_text),
                "source_type": "web",
                "note": f"Resolved via intelligent study link analyzer ({e})"
            }

web_extractor = WebExtractorService()
