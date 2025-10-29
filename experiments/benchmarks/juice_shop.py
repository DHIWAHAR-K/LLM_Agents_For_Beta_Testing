"""
OWASP Juice Shop Benchmark Adapter

Integrates with OWASP Juice Shop (https://github.com/juice-shop/juice-shop) for
security testing validation. Juice Shop is a deliberately insecure web application
with 100+ security challenges covering OWASP Top 10.

Installation:
    docker pull bkimminich/juice-shop
    docker run -d -p 3000:3000 bkimminich/juice-shop

Usage:
    from experiments.benchmarks.juice_shop import JuiceShopAdapter

    adapter = JuiceShopAdapter(base_url="http://localhost:3000")
    adapter.reset_instance()
    challenges = adapter.get_challenges()
"""

import requests
import sqlite3
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class JuiceShopChallenge:
    """Represents an OWASP Juice Shop challenge"""
    challenge_id: str
    name: str
    category: str
    difficulty: str  # 1-6 stars
    description: str
    hint: str
    owasp_category: str  # A01:2021, etc.
    vulnerability_type: str


# OWASP Juice Shop Challenge Catalog
# This is a curated list of the most relevant challenges for automated testing
JUICE_SHOP_CHALLENGES = [
    # ========== A01:2021 - Broken Access Control ==========
    JuiceShopChallenge(
        challenge_id="adminSection",
        name="Admin Section",
        category="Broken Access Control",
        difficulty="1",
        description="Access the administration section of the store",
        hint="Try to access /administration or guess admin paths",
        owasp_category="A01:2021",
        vulnerability_type="Broken Access Control"
    ),
    JuiceShopChallenge(
        challenge_id="viewBasket",
        name="View Another User's Basket",
        category="Broken Access Control",
        difficulty="2",
        description="View another user's shopping basket",
        hint="Manipulate basket ID parameter",
        owasp_category="A01:2021",
        vulnerability_type="Insecure Direct Object Reference"
    ),
    JuiceShopChallenge(
        challenge_id="forgedFeedback",
        name="Forged Feedback",
        category="Broken Access Control",
        difficulty="3",
        description="Post feedback as another user",
        hint="Manipulate user ID in feedback submission",
        owasp_category="A01:2021",
        vulnerability_type="Missing Authorization"
    ),

    # ========== A02:2021 - Cryptographic Failures ==========
    JuiceShopChallenge(
        challenge_id="passwordStrength",
        name="Password Strength",
        category="Cryptographic Failures",
        difficulty="2",
        description="Log in with the administrator's password",
        hint="Try common weak passwords or SQL injection",
        owasp_category="A02:2021",
        vulnerability_type="Weak Password Policy"
    ),
    JuiceShopChallenge(
        challenge_id="weakPasswordPolicy",
        name="Weak Password Policy",
        category="Cryptographic Failures",
        difficulty="1",
        description="Register with a password that doesn't meet security standards",
        hint="Try very short or simple passwords",
        owasp_category="A02:2021",
        vulnerability_type="Insufficient Password Requirements"
    ),

    # ========== A03:2021 - Injection ==========
    JuiceShopChallenge(
        challenge_id="loginAdmin",
        name="Login Admin (SQL Injection)",
        category="Injection",
        difficulty="2",
        description="Log in with the administrator account using SQL injection",
        hint="Try ' OR 1=1-- in email field",
        owasp_category="A03:2021",
        vulnerability_type="SQL Injection"
    ),
    JuiceShopChallenge(
        challenge_id="loginBender",
        name="Login Bender (SQL Injection)",
        category="Injection",
        difficulty="3",
        description="Log in as Bender using SQL injection",
        hint="Combine username knowledge with SQL injection",
        owasp_category="A03:2021",
        vulnerability_type="SQL Injection"
    ),
    JuiceShopChallenge(
        challenge_id="searchLogic",
        name="Search Logic Flaw",
        category="Injection",
        difficulty="3",
        description="Exploit search functionality with SQL injection",
        hint="Use SQL operators in search queries",
        owasp_category="A03:2021",
        vulnerability_type="SQL Injection"
    ),

    # ========== A03:2021 - XSS ==========
    JuiceShopChallenge(
        challenge_id="domXss",
        name="DOM XSS",
        category="XSS",
        difficulty="1",
        description="Perform a DOM-based XSS attack",
        hint="Try <iframe src=\"javascript:alert('XSS')\">",
        owasp_category="A03:2021",
        vulnerability_type="Cross-Site Scripting (DOM)"
    ),
    JuiceShopChallenge(
        challenge_id="persistedXss",
        name="Persisted XSS",
        category="XSS",
        difficulty="3",
        description="Perform a persisted XSS attack via user-generated content",
        hint="Submit malicious script in feedback or review",
        owasp_category="A03:2021",
        vulnerability_type="Cross-Site Scripting (Stored)"
    ),
    JuiceShopChallenge(
        challenge_id="reflectedXss",
        name="Reflected XSS",
        category="XSS",
        difficulty="2",
        description="Perform a reflected XSS attack",
        hint="Inject script tags in URL parameters",
        owasp_category="A03:2021",
        vulnerability_type="Cross-Site Scripting (Reflected)"
    ),

    # ========== A04:2021 - Insecure Design ==========
    JuiceShopChallenge(
        challenge_id="zeroStars",
        name="Zero Stars",
        category="Insecure Design",
        difficulty="1",
        description="Give a feedback with zero stars",
        hint="Manipulate rating value to 0",
        owasp_category="A04:2021",
        vulnerability_type="Improper Input Validation"
    ),
    JuiceShopChallenge(
        challenge_id="negativeOrder",
        name="Negative Order",
        category="Insecure Design",
        difficulty="3",
        description="Order products with negative quantities",
        hint="Intercept and modify quantity to negative value",
        owasp_category="A04:2021",
        vulnerability_type="Business Logic Flaw"
    ),

    # ========== A05:2021 - Security Misconfiguration ==========
    JuiceShopChallenge(
        challenge_id="errorHandling",
        name="Error Handling",
        category="Security Misconfiguration",
        difficulty="1",
        description="Provoke an error that reveals sensitive information",
        hint="Submit invalid data to trigger stack traces",
        owasp_category="A05:2021",
        vulnerability_type="Verbose Error Messages"
    ),
    JuiceShopChallenge(
        challenge_id="deprecatedInterface",
        name="Deprecated Interface",
        category="Security Misconfiguration",
        difficulty="2",
        description="Use a deprecated API endpoint",
        hint="Look for /api/v1 or /rest endpoints",
        owasp_category="A05:2021",
        vulnerability_type="Outdated Components"
    ),

    # ========== A06:2021 - Vulnerable Components ==========
    JuiceShopChallenge(
        challenge_id="typosquatting",
        name="Typosquatting",
        category="Vulnerable Components",
        difficulty="4",
        description="Identify a malicious dependency",
        hint="Check package.json for suspicious packages",
        owasp_category="A06:2021",
        vulnerability_type="Supply Chain Attack"
    ),

    # ========== A07:2021 - Identification & Authentication ==========
    JuiceShopChallenge(
        challenge_id="resetPassword",
        name="Password Reset",
        category="Identification & Authentication",
        difficulty="3",
        description="Reset another user's password",
        hint="Exploit weak security questions or token prediction",
        owasp_category="A07:2021",
        vulnerability_type="Broken Authentication"
    ),
    JuiceShopChallenge(
        challenge_id="twoFactorAuth",
        name="2FA Bypass",
        category="Identification & Authentication",
        difficulty="4",
        description="Bypass two-factor authentication",
        hint="Look for timing or logic flaws in 2FA flow",
        owasp_category="A07:2021",
        vulnerability_type="2FA Bypass"
    ),

    # ========== A08:2021 - Software & Data Integrity ==========
    JuiceShopChallenge(
        challenge_id="rceOccupy",
        name="Remote Code Execution",
        category="Software & Data Integrity",
        difficulty="5",
        description="Perform remote code execution",
        hint="Exploit deserialization or injection vulnerabilities",
        owasp_category="A08:2021",
        vulnerability_type="Remote Code Execution"
    ),

    # ========== A09:2021 - Security Logging & Monitoring ==========
    JuiceShopChallenge(
        challenge_id="accessLog",
        name="Access Log",
        category="Security Logging & Monitoring",
        difficulty="4",
        description="Access the application's access log",
        hint="Try to find log files in common locations",
        owasp_category="A09:2021",
        vulnerability_type="Exposed Logs"
    ),

    # ========== A10:2021 - Server-Side Request Forgery ==========
    JuiceShopChallenge(
        challenge_id="ssrf",
        name="SSRF",
        category="SSRF",
        difficulty="5",
        description="Perform a Server-Side Request Forgery attack",
        hint="Manipulate URLs to access internal resources",
        owasp_category="A10:2021",
        vulnerability_type="Server-Side Request Forgery"
    ),
]


class JuiceShopAdapter:
    """Adapter for interacting with OWASP Juice Shop"""

    def __init__(self, base_url: str = "http://localhost:3000", db_path: str = "experiments/results/experiments.db"):
        self.base_url = base_url.rstrip('/')
        self.db_path = db_path
        self.session = requests.Session()

    def check_availability(self) -> bool:
        """Check if Juice Shop is running"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def reset_instance(self) -> bool:
        """Reset Juice Shop to clean state (requires admin privileges)"""
        try:
            # Note: Juice Shop doesn't have a built-in reset API
            # You may need to restart the Docker container
            print("⚠️  Juice Shop reset requires Docker container restart:")
            print("    docker restart <container_id>")
            return True
        except Exception as e:
            print(f"Error resetting Juice Shop: {e}")
            return False

    def load_challenges_to_db(self) -> None:
        """Load challenge definitions into database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for challenge in JUICE_SHOP_CHALLENGES:
            cursor.execute("""
                INSERT OR REPLACE INTO owasp_challenges (
                    challenge_id, name, category, difficulty,
                    description, owasp_category, vulnerability_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                challenge.challenge_id,
                challenge.name,
                challenge.category,
                challenge.difficulty,
                challenge.description,
                challenge.owasp_category,
                challenge.vulnerability_type
            ))

        conn.commit()
        conn.close()
        print(f"✓ Loaded {len(JUICE_SHOP_CHALLENGES)} Juice Shop challenges to database")

    def register_user(self, email: str, password: str) -> Dict:
        """Register a new user"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/Users/",
                json={"email": email, "password": password, "passwordRepeat": password},
                timeout=10
            )
            return {"success": response.status_code == 201, "data": response.json()}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def login(self, email: str, password: str) -> Dict:
        """Login with credentials"""
        try:
            response = self.session.post(
                f"{self.base_url}/rest/user/login",
                json={"email": email, "password": password},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if 'authentication' in data:
                    self.session.headers.update({
                        'Authorization': f"Bearer {data['authentication']['token']}"
                    })
                return {"success": True, "data": data}
            return {"success": False, "status": response.status_code}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def get_products(self) -> Dict:
        """Get product list"""
        try:
            response = self.session.get(f"{self.base_url}/api/Products/", timeout=10)
            return {"success": response.status_code == 200, "data": response.json()}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def search_products(self, query: str) -> Dict:
        """Search products (vulnerable to SQL injection)"""
        try:
            response = self.session.get(
                f"{self.base_url}/rest/products/search",
                params={"q": query},
                timeout=10
            )
            return {"success": response.status_code == 200, "data": response.json()}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def add_to_basket(self, product_id: int, quantity: int = 1) -> Dict:
        """Add product to basket"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/BasketItems/",
                json={"ProductId": product_id, "quantity": quantity},
                timeout=10
            )
            return {"success": response.status_code == 200, "data": response.json()}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def submit_feedback(self, comment: str, rating: int = 5) -> Dict:
        """Submit feedback (vulnerable to XSS)"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/Feedbacks/",
                json={"comment": comment, "rating": rating, "captchaId": 0, "captcha": ""},
                timeout=10
            )
            return {"success": response.status_code == 201, "data": response.json()}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}

    def check_challenge_solved(self, challenge_name: str) -> bool:
        """Check if a challenge has been solved (requires scraping or API)"""
        # Note: Juice Shop tracks solved challenges in browser localStorage
        # For automated testing, you'd need to monitor the /api/Challenges endpoint
        # or parse the UI
        try:
            response = self.session.get(f"{self.base_url}/api/Challenges/", timeout=10)
            if response.status_code == 200:
                challenges = response.json()
                for challenge in challenges.get('data', []):
                    if challenge.get('name') == challenge_name:
                        return challenge.get('solved', False)
            return False
        except requests.RequestException:
            return False

    def mark_challenge_detected(self, run_id: int, challenge_id: str,
                               detected: bool, turn: int = 0,
                               method: str = "") -> None:
        """Mark a challenge as detected in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO owasp_detections (
                run_id, challenge_id, detected, detected_at_turn,
                detection_method, confidence
            ) VALUES (?, ?, ?, ?, ?, 1.0)
        """, (run_id, challenge_id, detected, turn, method))

        conn.commit()
        conn.close()

    def get_detection_statistics(self, experiment_id: int = None) -> Dict:
        """Get detection statistics across runs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if experiment_id:
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT c.challenge_id) as total_challenges,
                    COUNT(DISTINCT CASE WHEN d.detected = 1 THEN c.challenge_id END) as challenges_solved,
                    ROUND(100.0 * COUNT(DISTINCT CASE WHEN d.detected = 1 THEN c.challenge_id END) /
                          COUNT(DISTINCT c.challenge_id), 2) as solve_rate
                FROM owasp_challenges c
                LEFT JOIN owasp_detections d ON c.challenge_id = d.challenge_id
                LEFT JOIN runs r ON d.run_id = r.id
                WHERE r.experiment_id = ? OR r.experiment_id IS NULL
            """, (experiment_id,))
        else:
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT challenge_id) as total_challenges,
                    COUNT(DISTINCT CASE WHEN detected = 1 THEN challenge_id END) as challenges_solved,
                    ROUND(100.0 * COUNT(DISTINCT CASE WHEN detected = 1 THEN challenge_id END) /
                          COUNT(DISTINCT challenge_id), 2) as solve_rate
                FROM owasp_challenges
                LEFT JOIN owasp_detections USING(challenge_id)
            """)

        result = cursor.fetchone()
        conn.close()

        return {
            "total_challenges": result[0] if result else 0,
            "challenges_solved": result[1] if result else 0,
            "solve_rate": result[2] if result else 0.0
        }


def print_challenge_summary():
    """Print summary of available challenges"""
    from collections import Counter

    print("\n" + "="*80)
    print("OWASP JUICE SHOP CHALLENGE CATALOG")
    print("="*80)

    category_counts = Counter(c.category for c in JUICE_SHOP_CHALLENGES)
    owasp_counts = Counter(c.owasp_category for c in JUICE_SHOP_CHALLENGES)
    difficulty_counts = Counter(c.difficulty for c in JUICE_SHOP_CHALLENGES)

    print(f"\nTotal Challenges: {len(JUICE_SHOP_CHALLENGES)}")

    print("\nBy OWASP Category:")
    for category, count in sorted(owasp_counts.items()):
        print(f"  {category}: {count}")

    print("\nBy Difficulty:")
    for diff, count in sorted(difficulty_counts.items()):
        stars = "⭐" * int(diff)
        print(f"  {stars}: {count}")

    print("\nDetailed List:")
    print("-" * 80)
    for challenge in JUICE_SHOP_CHALLENGES:
        print(f"[{challenge.challenge_id}] {challenge.name} (difficulty: {challenge.difficulty})")
        print(f"  {challenge.description}")
        print(f"  Category: {challenge.owasp_category} - {challenge.vulnerability_type}")
        print()


if __name__ == "__main__":
    print_challenge_summary()
