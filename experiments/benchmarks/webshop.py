"""
WebShop Benchmark Adapter

Integrates with WebShop environment (https://webshop-pnlp.github.io/) for
e-commerce task success validation. WebShop is a simulated e-commerce platform
with 1.18M products, used to evaluate LLM agents on realistic shopping tasks.

Installation:
    git clone https://github.com/princeton-nlp/WebShop.git
    cd WebShop
    pip install -e .
    # Follow WebShop setup instructions

Paper Baseline:
    - GPT-3 with search+choice: 50.1% task success
    - RL agent: 29.0% task success
    - Human performance: ~60-70%

Usage:
    from experiments.benchmarks.webshop import WebShopAdapter

    adapter = WebShopAdapter(base_url="http://localhost:3000")
    task = adapter.get_task(task_id="task_001")
    result = adapter.evaluate_purchase(task, purchased_asin="B07XYZ")
"""

import requests
import sqlite3
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
import re


@dataclass
class WebShopTask:
    """Represents a WebShop task"""
    task_id: str
    instruction: str  # e.g., "I want a red t-shirt in size large"
    target_attributes: Dict  # Required product attributes
    difficulty: str  # easy, medium, hard


# Sample WebShop tasks (curated for testing)
WEBSHOP_TASKS = [
    # ========== EASY TASKS (Specific product with few constraints) ==========
    WebShopTask(
        task_id="task_easy_001",
        instruction="I need a wireless mouse for my laptop",
        target_attributes={"category": "Electronics", "type": "mouse", "connectivity": "wireless"},
        difficulty="easy"
    ),
    WebShopTask(
        task_id="task_easy_002",
        instruction="I want a water bottle, preferably stainless steel",
        target_attributes={"category": "Kitchen", "type": "water bottle", "material": "stainless steel"},
        difficulty="easy"
    ),
    WebShopTask(
        task_id="task_easy_003",
        instruction="I need a USB-C charging cable",
        target_attributes={"category": "Electronics", "type": "cable", "connector": "USB-C"},
        difficulty="easy"
    ),

    # ========== MEDIUM TASKS (Multiple constraints) ==========
    WebShopTask(
        task_id="task_medium_001",
        instruction="I want a blue backpack with laptop compartment, under $50",
        target_attributes={"category": "Bags", "color": "blue", "feature": "laptop compartment", "price_max": 50},
        difficulty="medium"
    ),
    WebShopTask(
        task_id="task_medium_002",
        instruction="I need running shoes, size 10, for men, with good cushioning",
        target_attributes={"category": "Shoes", "type": "running", "size": "10", "gender": "men", "feature": "cushioning"},
        difficulty="medium"
    ),
    WebShopTask(
        task_id="task_medium_003",
        instruction="I want a 27-inch monitor with 4K resolution and HDMI port",
        target_attributes={"category": "Electronics", "size": "27 inch", "resolution": "4K", "port": "HDMI"},
        difficulty="medium"
    ),

    # ========== HARD TASKS (Many constraints, specific requirements) ==========
    WebShopTask(
        task_id="task_hard_001",
        instruction="I need a ergonomic office chair, black color, with lumbar support, adjustable armrests, and mesh back, under $300",
        target_attributes={
            "category": "Furniture",
            "color": "black",
            "features": ["lumbar support", "adjustable armrests", "mesh back"],
            "price_max": 300
        },
        difficulty="hard"
    ),
    WebShopTask(
        task_id="task_hard_002",
        instruction="I want a smartphone with at least 128GB storage, 5G capability, good camera (48MP+), and long battery life (4000mAh+)",
        target_attributes={
            "category": "Electronics",
            "storage_min": 128,
            "features": ["5G", "camera 48MP+", "battery 4000mAh+"]
        },
        difficulty="hard"
    ),
    WebShopTask(
        task_id="task_hard_003",
        instruction="I need a coffee maker with programmable timer, thermal carafe, automatic shut-off, and brew strength control",
        target_attributes={
            "category": "Kitchen",
            "features": ["programmable timer", "thermal carafe", "automatic shut-off", "brew strength control"]
        },
        difficulty="hard"
    ),
]


class WebShopAdapter:
    """Adapter for interacting with WebShop environment"""

    def __init__(self, base_url: str = "http://localhost:3000", db_path: str = "experiments/results/experiments.db"):
        self.base_url = base_url.rstrip('/')
        self.db_path = db_path
        self.session = requests.Session()

    def check_availability(self) -> bool:
        """Check if WebShop is running"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def load_tasks_to_db(self) -> None:
        """Load task definitions into database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for task in WEBSHOP_TASKS:
            cursor.execute("""
                INSERT OR REPLACE INTO webshop_tasks (
                    task_id, instruction, target_attributes, difficulty
                ) VALUES (?, ?, ?, ?)
            """, (
                task.task_id,
                task.instruction,
                json.dumps(task.target_attributes),
                task.difficulty
            ))

        conn.commit()
        conn.close()
        print(f"✓ Loaded {len(WEBSHOP_TASKS)} WebShop tasks to database")

    def get_task(self, task_id: str) -> Optional[WebShopTask]:
        """Get a specific task by ID"""
        for task in WEBSHOP_TASKS:
            if task.task_id == task_id:
                return task
        return None

    def search_products(self, query: str, page: int = 1) -> Dict:
        """Search for products"""
        try:
            response = self.session.get(
                f"{self.base_url}/search",
                params={"keywords": query, "page": page},
                timeout=10
            )
            return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def get_product_details(self, asin: str) -> Dict:
        """Get detailed product information"""
        try:
            response = self.session.get(
                f"{self.base_url}/product/{asin}",
                timeout=10
            )
            return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def select_product_options(self, asin: str, options: Dict) -> Dict:
        """Select product options (size, color, etc.)"""
        try:
            response = self.session.post(
                f"{self.base_url}/product/{asin}/options",
                json=options,
                timeout=10
            )
            return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def add_to_cart(self, asin: str, options: Dict = None) -> Dict:
        """Add product to cart"""
        try:
            response = self.session.post(
                f"{self.base_url}/cart/add",
                json={"asin": asin, "options": options or {}},
                timeout=10
            )
            return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def purchase(self) -> Dict:
        """Complete purchase (final action)"""
        try:
            response = self.session.post(
                f"{self.base_url}/cart/purchase",
                timeout=10
            )
            return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def calculate_reward(self, task: WebShopTask, purchased_asin: str,
                        purchased_attributes: Dict) -> Tuple[float, Dict]:
        """
        Calculate reward score for a purchase (0.0 to 1.0)
        Based on WebShop paper's reward function
        """
        if not purchased_asin:
            return 0.0, {"reason": "No product purchased"}

        target = task.target_attributes
        actual = purchased_attributes

        # Count matching attributes
        total_attributes = len(target)
        matched_attributes = 0
        matches = {}

        for key, target_value in target.items():
            if key in actual:
                actual_value = actual[key]

                if isinstance(target_value, list):
                    # Multiple required features
                    matched = sum(1 for feature in target_value if feature.lower() in str(actual_value).lower())
                    match_ratio = matched / len(target_value)
                    matched_attributes += match_ratio
                    matches[key] = f"{matched}/{len(target_value)}"
                elif isinstance(target_value, (int, float)):
                    # Numeric constraint
                    if "_min" in key:
                        if actual_value >= target_value:
                            matched_attributes += 1
                            matches[key] = "✓"
                    elif "_max" in key:
                        if actual_value <= target_value:
                            matched_attributes += 1
                            matches[key] = "✓"
                    else:
                        if actual_value == target_value:
                            matched_attributes += 1
                            matches[key] = "✓"
                else:
                    # String matching
                    if str(target_value).lower() in str(actual_value).lower():
                        matched_attributes += 1
                        matches[key] = "✓"

        reward = matched_attributes / total_attributes if total_attributes > 0 else 0.0

        return reward, {
            "matched_attributes": matched_attributes,
            "total_attributes": total_attributes,
            "reward": reward,
            "matches": matches
        }

    def log_result(self, run_id: int, task_id: str, success: bool,
                  reward_score: float, num_steps: int,
                  purchased_asin: str = None, correct_attributes: str = None) -> None:
        """Log WebShop task result to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO webshop_results (
                run_id, task_id, success, reward_score, num_steps,
                purchased_product, correct_attributes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (run_id, task_id, success, reward_score, num_steps,
              purchased_asin, correct_attributes))

        conn.commit()
        conn.close()

    def get_statistics(self, experiment_id: int = None) -> Dict:
        """Get WebShop performance statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if experiment_id:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_tasks,
                    ROUND(100.0 * SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate,
                    ROUND(AVG(reward_score), 3) as avg_reward,
                    ROUND(AVG(num_steps), 1) as avg_steps
                FROM webshop_results wr
                JOIN runs r ON wr.run_id = r.id
                WHERE r.experiment_id = ?
            """, (experiment_id,))
        else:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_tasks,
                    ROUND(100.0 * SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate,
                    ROUND(AVG(reward_score), 3) as avg_reward,
                    ROUND(AVG(num_steps), 1) as avg_steps
                FROM webshop_results
            """)

        result = cursor.fetchone()
        conn.close()

        return {
            "total_tasks": result[0] if result else 0,
            "successful_tasks": result[1] if result else 0,
            "success_rate": result[2] if result else 0.0,
            "avg_reward": result[3] if result else 0.0,
            "avg_steps": result[4] if result else 0.0
        }


def print_task_summary():
    """Print summary of WebShop tasks"""
    from collections import Counter

    print("\n" + "="*80)
    print("WEBSHOP BENCHMARK TASK CATALOG")
    print("="*80)

    difficulty_counts = Counter(t.difficulty for t in WEBSHOP_TASKS)

    print(f"\nTotal Tasks: {len(WEBSHOP_TASKS)}")

    print("\nBy Difficulty:")
    for diff, count in sorted(difficulty_counts.items()):
        print(f"  {diff.capitalize()}: {count}")

    print("\nBaseline Performance (from WebShop paper):")
    print("  GPT-3 (search+choice): 50.1% success rate")
    print("  RL Agent: 29.0% success rate")
    print("  Human: ~60-70% success rate")

    print("\nDetailed Task List:")
    print("-" * 80)
    for task in WEBSHOP_TASKS:
        print(f"[{task.task_id}] {task.difficulty.upper()}")
        print(f"  Instruction: {task.instruction}")
        print(f"  Required Attributes: {json.dumps(task.target_attributes, indent=4)}")
        print()


if __name__ == "__main__":
    print_task_summary()
