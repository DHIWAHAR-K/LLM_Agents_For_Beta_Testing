"""Browser adapter for UI-based testing with Playwright."""
from __future__ import annotations

import time
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from typing import Any, Dict, Tuple

from playwright.async_api import async_playwright, Page, Browser, Playwright

from config import settings
from .html_parser import HTMLParser
from .schemas import Action


class BrowserAdapter:
    """Execute Actions against a web UI using Playwright browser automation with screenshots."""

    def __init__(self, base_url: str | None = None, headless: bool = False, screenshots_dir: str | None = None) -> None:
        self.base_url = (base_url or settings.api_base_url).rstrip("/")
        self.headless = headless  # Default to visible browser
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.page: Page | None = None
        self.html_parser = HTMLParser(self.base_url)
        self.screenshots_dir = Path(screenshots_dir) if screenshots_dir else Path("screenshots")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        # Track that we've already added a product from the search page to avoid repeat adds
        self.search_add_completed = False

    async def start(self) -> None:
        """Start the browser."""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
            self.page = await self.browser.new_page()
            # Navigate to homepage to initialize
            await self.page.goto(self.base_url)

    async def stop(self) -> None:
        """Close the browser."""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def execute(self, action: Action) -> Tuple[str, float]:
        """Execute an action and return observation + latency."""
        if not self.page:
            await self.start()

        start = time.time()

        try:
            if action.type == "navigate":
                observation = await self._handle_navigate(action)
            elif action.type == "click":
                observation = await self._handle_click(action)
            elif action.type == "fill":
                observation = await self._handle_fill(action)
            elif action.type == "scroll":
                observation = await self._handle_scroll(action)
            elif action.type == "tap":
                # For compatibility, treat tap as API call or click
                observation = await self._handle_tap(action)
            elif action.type == "report":
                issue = action.payload.get("issue", "") if action.payload else ""
                observation = f"Report submitted: {issue}"
            else:
                observation = f"Unknown action type: {action.type}"

            latency = time.time() - start
            return observation, latency

        except Exception as exc:
            latency = time.time() - start
            return f"BROWSER_ERROR: {exc}", latency

    async def _handle_navigate(self, action: Action) -> str:
        """Handle navigate action - go to a page."""
        target = action.target
        if not target.startswith("http"):
            target = f"{self.base_url}{target}"

        await self.page.goto(target)
        await self.page.wait_for_load_state("networkidle")

        # Parse the current page and return structured observation
        current_path = self.page.url.replace(self.base_url, "")
        parsed_data = self.html_parser.fetch_and_parse(current_path)

        return self.html_parser.format_for_agent(parsed_data)

    async def _handle_click(self, action: Action) -> str:
        """Handle click action - click an element by selector."""
        selector = action.payload.get("selector") if action.payload else None

        if not selector:
            return "ERROR: No selector provided for click action"

        # Prevent multiple add-to-cart clicks on the search page after the first successful add
        if (
            "add-to-cart" in selector
            and self.page
            and "/search" in self.page.url
            and "q=" in self.page.url
            and self.search_add_completed
        ):
            return "SKIP: Already added an item from search results; proceed to filters/cart."

        extra_note = ""
        clicked_via_query_match = False

        # If on search page with ?q= and clicking add-to-cart, click only a matching product and capture unrelated
        if (
            "add-to-cart" in selector
            and self.page
            and "/search" in self.page.url
            and "q=" in self.page.url
        ):
            parsed = urlparse(self.page.url)
            query_value = parse_qs(parsed.query).get("q", [""])[0].lower()
            try:
                result = await self.page.evaluate(
                    """(q) => {
                        const cards = [...document.querySelectorAll('.product-card')];
                        const unrelated = [];
                        let clicked = false;
                        for (const card of cards) {
                            const titleEl = card.querySelector('.product-title');
                            const name = (titleEl?.innerText || '').trim();
                            const match = name.toLowerCase().includes(q);
                            if (!match && name) unrelated.push(name);
                            if (!clicked && match) {
                                const btn = card.querySelector('.add-to-cart');
                                if (btn) { btn.click(); clicked = true; }
                            }
                        }
                        return { clicked, unrelated };
                    }""",
                    query_value,
                )
                clicked_via_query_match = result.get("clicked", False)
                unrelated = result.get("unrelated", [])
                if unrelated:
                    extra_note = f"Unrelated products present for query '{query_value}': {', '.join(unrelated)}"
            except Exception:
                clicked_via_query_match = False
                extra_note = ""
        # If on products page after filters, pick first product within filter bounds
        elif (
            "add-to-cart" in selector
            and self.page
            and "/products" in self.page.url
        ):
            try:
                result = await self.page.evaluate(
                    """() => {
                        const minEl = document.querySelector('#minPrice');
                        const maxEl = document.querySelector('#maxPrice');
                        const minVal = minEl ? parseFloat(minEl.value) : NaN;
                        const maxVal = maxEl ? parseFloat(maxEl.value) : NaN;
                        const hasMin = !Number.isNaN(minVal);
                        const hasMax = !Number.isNaN(maxVal);
                        const cards = [...document.querySelectorAll('.product-card')];
                        for (const card of cards) {
                            const priceEl = card.querySelector('.product-price');
                            const btn = card.querySelector('.add-to-cart');
                            if (!priceEl || !btn) continue;
                            const priceText = priceEl.innerText.replace(/[^0-9.]/g, '');
                            const price = parseFloat(priceText);
                            if (Number.isNaN(price)) continue;
                            if (hasMin && price < minVal) continue;
                            if (hasMax && price > maxVal) continue;
                            btn.click();
                            return {clicked:true, chosen: price};
                        }
                        return {clicked:false, chosen:null};
                    }"""
                )
                if result and result.get("clicked"):
                    clicked_via_query_match = True  # reuse flag to skip default click
                    extra_note = extra_note or f"Added filtered product at price {result.get('chosen')}"
            except Exception:
                pass

        try:
            if not clicked_via_query_match:
                await self.page.click(selector, timeout=5000)
            # Wait for network to be idle (API calls to complete)
            await self.page.wait_for_load_state("networkidle")
            # Additional small wait to ensure JavaScript has processed the response
            await self.page.wait_for_timeout(500)

            # If we clicked a search/filter control, wait for results to render
            if "search-button" in selector or "search" in selector:
                try:
                    await self.page.wait_for_selector(".add-to-cart", timeout=5000)
                except Exception:
                    pass
            # If we clicked an apply filters button (btn-success), also wait for results
            if "btn-success" in selector:
                try:
                    await self.page.wait_for_selector(".add-to-cart", timeout=5000)
                except Exception:
                    pass

            # Mark search add complete if we clicked an add-to-cart on a search results page
            if (
                "add-to-cart" in selector
                and self.page
                and "/search" in self.page.url
                and "q=" in self.page.url
            ):
                self.search_add_completed = True
                # Immediately redirect to products to continue flow and avoid repeat adds on search
                await self.page.goto(f"{self.base_url}/products")
                await self.page.wait_for_load_state("networkidle")
                await self.page.wait_for_timeout(300)

            # Return updated page state
            current_path = self.page.url.replace(self.base_url, "")
            parsed_data = self.html_parser.fetch_and_parse(current_path)
            formatted = self.html_parser.format_for_agent(parsed_data)
            if extra_note:
                formatted = f"{formatted}\nNOTE: {extra_note}"
            return formatted

        except Exception as e:
            # Fallback: if a back-to-products control isn't found, navigate directly
            if "back-to-products" in (selector or ""):
                await self.page.goto(f"{self.base_url}/products")
                await self.page.wait_for_load_state("networkidle")
                current_path = self.page.url.replace(self.base_url, "")
                parsed_data = self.html_parser.fetch_and_parse(current_path)
                return self.html_parser.format_for_agent(parsed_data)

            # Fallback: if add-to-cart button not immediately clickable, try first visible
            if "add-to-cart" in (selector or ""):
                try:
                    await self.page.wait_for_selector(".add-to-cart", timeout=5000)
                    await self.page.click(".add-to-cart", timeout=5000)
                    await self.page.wait_for_load_state("networkidle")
                    await self.page.wait_for_timeout(500)
                    if (
                        self.page
                        and "/search" in self.page.url
                        and "q=" in self.page.url
                    ):
                        self.search_add_completed = True
                        await self.page.goto(f"{self.base_url}/products")
                        await self.page.wait_for_load_state("networkidle")
                        await self.page.wait_for_timeout(300)
                    current_path = self.page.url.replace(self.base_url, "")
                    parsed_data = self.html_parser.fetch_and_parse(current_path)
                    return self.html_parser.format_for_agent(parsed_data)
                except Exception:
                    return f"CLICK_ERROR: Could not click {selector}: {e}"

            return f"CLICK_ERROR: Could not click {selector}: {e}"

    async def _handle_fill(self, action: Action) -> str:
        """Handle fill action - fill an input field."""
        if not action.payload:
            return "ERROR: No payload provided for fill action"

        selector = action.payload.get("selector")
        value = action.payload.get("value", "")

        if not selector:
            return "ERROR: No selector provided for fill action"

        try:
            # Try to fill with the provided selector first
            try:
                await self.page.fill(selector, str(value), timeout=5000)
                return f"Filled {selector} with value: {value}"
            except Exception as first_error:
                # If selector fails, try alternative selectors for common cases
                alternative_selectors = []
                
                # If it's a search-related selector that failed, try #searchInput
                if "search" in selector.lower() or "twotab" in selector.lower():
                    alternative_selectors.append("#searchInput")
                
                # Try alternative selectors
                for alt_selector in alternative_selectors:
                    try:
                        await self.page.fill(alt_selector, str(value), timeout=5000)
                        return f"Filled {alt_selector} with value: {value} (used alternative selector instead of {selector})"
                    except Exception:
                        continue
                
                # If all else fails, try JavaScript-based fill
                import json
                value_json = json.dumps(str(value))
                selector_json = json.dumps(selector)
                
                # Try with original selector first
                try:
                    await self.page.evaluate(f"""
                        (() => {{
                            const el = document.querySelector({selector_json});
                            if (el) {{
                                el.value = {value_json};
                                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                        }})()
                    """)
                    return f"Filled {selector} with value: {value} (using JavaScript)"
                except Exception:
                    # Try alternative selectors with JavaScript
                    for alt_selector in alternative_selectors:
                        try:
                            alt_selector_json = json.dumps(alt_selector)
                            await self.page.evaluate(f"""
                                (() => {{
                                    const el = document.querySelector({alt_selector_json});
                                    if (el) {{
                                        el.value = {value_json};
                                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                }})()
                            """)
                            return f"Filled {alt_selector} with value: {value} (using JavaScript with alternative selector)"
                        except Exception:
                            continue
                
                # If everything fails, raise the original error
                raise first_error

        except Exception as e:
            return f"FILL_ERROR: Could not fill {selector}: {e}"

    async def _handle_scroll(self, action: Action) -> str:
        """Handle scroll action - scroll the page up or down."""
        direction = action.target.lower() if action.target else "down"
        pixels = 500  # Default scroll amount

        if action.payload and "pixels" in action.payload:
            pixels = action.payload.get("pixels", 500)

        try:
            # Execute JavaScript to scroll the page
            if direction == "down":
                await self.page.evaluate(f"window.scrollBy(0, {pixels})")
            elif direction == "up":
                await self.page.evaluate(f"window.scrollBy(0, -{pixels})")
            else:
                return f"ERROR: Invalid scroll direction '{direction}'. Use 'down' or 'up'."

            # Wait a moment for any lazy-loaded content
            await self.page.wait_for_timeout(500)

            # Return updated page state
            current_path = self.page.url.replace(self.base_url, "")
            parsed_data = self.html_parser.fetch_and_parse(current_path)
            return f"Scrolled {direction} {pixels}px. " + self.html_parser.format_for_agent(parsed_data)

        except Exception as e:
            return f"SCROLL_ERROR: Could not scroll: {e}"

    async def _handle_tap(self, action: Action) -> str:
        """Handle tap action - can be treated as click or button press."""
        # Try to find button by text content
        target = action.target

        try:
            # Try as button text
            await self.page.click(f"button:has-text('{target}')", timeout=5000)
            await self.page.wait_for_load_state("networkidle")

            current_path = self.page.url.replace(self.base_url, "")
            parsed_data = self.html_parser.fetch_and_parse(current_path)
            return self.html_parser.format_for_agent(parsed_data)

        except Exception:
            # Fall back to treating as CSS selector
            try:
                await self.page.click(target, timeout=5000)
                await self.page.wait_for_load_state("networkidle")

                current_path = self.page.url.replace(self.base_url, "")
                parsed_data = self.html_parser.fetch_and_parse(current_path)
                return self.html_parser.format_for_agent(parsed_data)

            except Exception as e:
                return f"TAP_ERROR: Could not tap {target}: {e}"

    async def capture_screenshot(self, session_id: str, turn: int) -> str:
        """Capture screenshot and return path."""
        if not self.page:
            raise RuntimeError("Browser not started")

        # Save screenshot directly in screenshots_dir (already in test folder)
        screenshot_path = self.screenshots_dir / f"turn_{turn}.png"
        await self.page.screenshot(path=str(screenshot_path))

        return str(screenshot_path)

    async def get_current_state(self) -> str:
        """Get the current page state as formatted text."""
        if not self.page:
            return "Browser not started"

        # Get the actual rendered HTML from Playwright (includes JavaScript-rendered content)
        try:
            html_content = await self.page.content()
            # Parse the rendered HTML instead of fetching via requests
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            parsed_data = {
                "url": self.page.url,
                "page_title": self._get_title(soup),
                "links": self.html_parser._extract_links(soup),
                "buttons": self.html_parser._extract_buttons(soup),
                "forms": self.html_parser._extract_forms(soup),
                "inputs": self.html_parser._extract_inputs(soup),
                "products": self.html_parser._extract_products(soup),
                "cart_info": self.html_parser._extract_cart_info(soup),
                "stats": self.html_parser._extract_stats(soup),
            }
            return self.html_parser.format_for_agent(parsed_data)
        except Exception as e:
            # Fallback to original method
            current_path = self.page.url.replace(self.base_url, "")
            parsed_data = self.html_parser.fetch_and_parse(current_path)
            return self.html_parser.format_for_agent(parsed_data)
    
    def _get_title(self, soup) -> str:
        """Extract page title from soup."""
        title_tag = soup.find('title')
        return title_tag.get_text(strip=True) if title_tag else "Untitled"
