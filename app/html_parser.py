"""HTML Parser for extracting UI structure and elements."""
from __future__ import annotations

from typing import Dict, List

import requests
from bs4 import BeautifulSoup


class HTMLParser:
    """Parse HTML pages and extract actionable UI elements."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")

    def fetch_and_parse(self, path: str = "/") -> Dict[str, any]:
        """
        Fetch HTML from a path and extract UI structure.

        Returns:
            Dict with page_title, links, forms, buttons, and text_content
        """
        url = f"{self.base_url}{path}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            return {"error": f"Failed to fetch {url}: {e}"}

        soup = BeautifulSoup(response.text, 'html.parser')

        return {
            "url": url,
            "page_title": self._get_title(soup),
            "links": self._extract_links(soup),
            "buttons": self._extract_buttons(soup),
            "forms": self._extract_forms(soup),
            "inputs": self._extract_inputs(soup),
            "products": self._extract_products(soup),
            "cart_info": self._extract_cart_info(soup),
            "stats": self._extract_stats(soup),
        }

    def _get_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        title_tag = soup.find('title')
        return title_tag.get_text(strip=True) if title_tag else "Untitled"

    def _extract_links(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract all links from the page."""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            if text:  # Only include links with text
                links.append({"text": text, "href": href})
        return links

    def _extract_buttons(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract all buttons from the page."""
        buttons = []
        for button in soup.find_all(['button', 'input']):
            if button.name == 'input' and button.get('type') not in ['button', 'submit']:
                continue

            text = button.get_text(strip=True) or button.get('value', '')
            btn_id = button.get('id', '')
            btn_class = ' '.join(button.get('class', []))

            if text or btn_id:
                buttons.append({
                    "text": text,
                    "id": btn_id,
                    "class": btn_class,
                    "type": button.get('type', 'button')
                })
        return buttons

    def _extract_forms(self, soup: BeautifulSoup) -> List[Dict[str, any]]:
        """Extract all forms and their inputs."""
        forms = []
        for form in soup.find_all('form'):
            action = form.get('action', '')
            method = form.get('method', 'get').upper()

            inputs = []
            for input_elem in form.find_all(['input', 'textarea', 'select']):
                input_type = input_elem.get('type', 'text')
                input_name = input_elem.get('name', '')
                input_id = input_elem.get('id', '')
                placeholder = input_elem.get('placeholder', '')

                if input_name:  # Only include named inputs
                    inputs.append({
                        "type": input_type,
                        "name": input_name,
                        "id": input_id,
                        "placeholder": placeholder
                    })

            if inputs:  # Only include forms with inputs
                forms.append({
                    "action": action,
                    "method": method,
                    "inputs": inputs
                })
        return forms

    def _extract_inputs(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract all input fields (including those outside forms) by id or name."""
        inputs = []
        for input_elem in soup.find_all(['input', 'textarea', 'select']):
            input_type = input_elem.get('type', 'text')
            input_id = input_elem.get('id', '')
            input_name = input_elem.get('name', '')
            placeholder = input_elem.get('placeholder', '')
            
            # Include inputs that have either id or name
            if input_id or input_name:
                selector = f"#{input_id}" if input_id else f"[name='{input_name}']"
                inputs.append({
                    "type": input_type,
                    "id": input_id,
                    "name": input_name,
                    "selector": selector,
                    "placeholder": placeholder
                })
        return inputs

    def _extract_products(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract product information from product cards."""
        products = []
        for product_card in soup.find_all(class_='product-card'):
            title_elem = product_card.find(class_='product-title')
            price_elem = product_card.find(class_='product-price')
            rating_elem = product_card.find(class_='product-rating')

            if title_elem:
                product = {
                    "title": title_elem.get_text(strip=True),
                    "price": price_elem.get_text(strip=True) if price_elem else "N/A",
                    "rating": rating_elem.get_text(strip=True) if rating_elem else "N/A"
                }
                products.append(product)
        return products

    def _extract_cart_info(self, soup: BeautifulSoup) -> Dict[str, any]:
        """Extract shopping cart information."""
        cart_widget = soup.find(class_='cart-widget')
        if not cart_widget:
            return {}

        cart_items = []
        for item in cart_widget.find_all(class_='cart-item'):
            item_text = item.get_text(strip=True)
            cart_items.append(item_text)

        total_elem = soup.find(id='cartTotal')
        count_elem = soup.find(id='cartCount')

        return {
            "items": cart_items,
            "total": total_elem.get_text(strip=True) if total_elem else "$0.00",
            "count": count_elem.get_text(strip=True) if count_elem else "0"
        }

    def _extract_stats(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract statistics from stats cards."""
        stats = {}

        stat_ids = ['totalProducts', 'totalOrders', 'totalRevenue', 'lowStockCount']
        stat_labels = ['products', 'orders', 'revenue', 'low_stock']

        for stat_id, label in zip(stat_ids, stat_labels):
            elem = soup.find(id=stat_id)
            if elem:
                stats[label] = elem.get_text(strip=True)

        return stats

    def format_for_agent(self, parsed_data: Dict[str, any]) -> str:
        """Format parsed HTML data into a text observation for the agent."""
        if "error" in parsed_data:
            return f"Error: {parsed_data['error']}"

        lines = [
            f"Page: {parsed_data['page_title']}",
            f"URL: {parsed_data['url']}",
            ""
        ]

        # Stats
        if parsed_data.get('stats'):
            lines.append("Store Statistics:")
            for key, value in parsed_data['stats'].items():
                lines.append(f"  - {key}: {value}")
            lines.append("")

        # Products - IMPORTANT: Show ALL products so agents can detect search relevance bugs
        if parsed_data.get('products'):
            lines.append(f"Products Visible ({len(parsed_data['products'])} total):")
            for i, prod in enumerate(parsed_data['products'], 1):
                lines.append(f"  {i}. {prod['title']} - {prod['price']} (Rating: {prod['rating']})")
            lines.append("")

        # Cart
        if parsed_data.get('cart_info'):
            cart = parsed_data['cart_info']
            lines.append(f"Shopping Cart: {cart.get('count', '0')} items, Total: {cart.get('total', '$0.00')}")
            lines.append("")

        # Forms
        if parsed_data.get('forms'):
            lines.append("Forms Available:")
            for i, form in enumerate(parsed_data['forms'], 1):
                lines.append(f"  Form {i}: {form['method']} {form['action']}")
                for inp in form['inputs']:
                    lines.append(f"    - {inp['type']}: {inp['name']} ({inp.get('placeholder', '')})")
            lines.append("")

        # Input Fields (including those outside forms)
        if parsed_data.get('inputs'):
            lines.append("Input Fields Available:")
            for inp in parsed_data['inputs']:
                selector = inp.get('selector', inp.get('id', inp.get('name', '')))
                placeholder = inp.get('placeholder', '')
                label = f"{inp['type']} input"
                if placeholder:
                    label += f" (placeholder: '{placeholder}')"
                lines.append(f"  - {label} (selector: {selector})")
            lines.append("")

        # Buttons (especially important for add-to-cart)
        if parsed_data.get('buttons'):
            add_to_cart_buttons = [b for b in parsed_data['buttons'] if 'add-to-cart' in b.get('class', '').lower()]
            if add_to_cart_buttons:
                lines.append("Add to Cart Buttons Available:")
                for btn in add_to_cart_buttons[:3]:  # Show first 3
                    selector = f".add-to-cart" if 'add-to-cart' in btn.get('class', '') else f"button:has-text('{btn.get('text', '')}')"
                    lines.append(f"  - {btn.get('text', 'Button')} (selector: {selector})")
                if len(add_to_cart_buttons) > 3:
                    lines.append(f"  ... and {len(add_to_cart_buttons) - 3} more add-to-cart buttons")
                lines.append("")
            
            other_buttons = [b for b in parsed_data['buttons'] if 'add-to-cart' not in b.get('class', '').lower()]
            if other_buttons:
                lines.append(f"Other Buttons: {len(other_buttons)} total")
                lines.append("")

        # Links (limit to important ones)
        if parsed_data.get('links'):
            lines.append(f"Links: {len(parsed_data['links'])} total")
            lines.append("")

        return "\n".join(lines)
