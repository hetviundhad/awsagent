import os
import sys
import time
from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOTS_DIR = os.path.join(PROJECT_ROOT, "artifacts", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

FRONTEND_URL = "http://localhost:5173"

def main():
    print(f"Capturing verified UI screenshots from {FRONTEND_URL}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Step 1: Open Login and click "Continue as Demo Student" button directly in UI
        page.goto(f"{FRONTEND_URL}/login")
        page.wait_for_timeout(1000)

        demo_btn = page.locator("button:has-text('Continue as Demo Student')")
        if demo_btn.is_visible():
            demo_btn.click()
            print(" Clicked 'Continue as Demo Student' button")
            page.wait_for_timeout(2500)

        # Ensure active course is set
        page.evaluate("""() => {
            localStorage.setItem("studymind_active_course", "a091a4aa-a333-4a0c-85ec-9af9ad8505bd");
            localStorage.setItem("studymind_active_course_e5ee47b2-ad1d-4536-b3eb-a165de1792b1", "a091a4aa-a333-4a0c-85ec-9af9ad8505bd");
        }""")

        # 1. Dashboard
        page.goto(f"{FRONTEND_URL}/dashboard")
        page.wait_for_timeout(3000)
        dash_path = os.path.join(SCREENSHOTS_DIR, "01_dashboard.png")
        page.screenshot(path=dash_path, full_page=True)
        print(f" [Captured] Dashboard -> {dash_path}")

        # 2. Quiz Modal (click "Start Diagnostic" or "Take Quiz" or "Practice Concept")
        try:
            quiz_trigger = page.locator("button:has-text('Start Diagnostic'), button:has-text('Take Quiz'), button:has-text('Practice Concept')").first
            if quiz_trigger.is_visible():
                quiz_trigger.click()
                page.wait_for_timeout(1500)
                modal_path = os.path.join(SCREENSHOTS_DIR, "02_quiz_modal.png")
                page.screenshot(path=modal_path)
                print(f" [Captured] Quiz Modal -> {modal_path}")
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
        except Exception as e:
            print(f" Notice Quiz Modal: {e}")

        # 3. Quiz Player / Assessments
        page.goto(f"{FRONTEND_URL}/assessments")
        page.wait_for_timeout(2500)
        player_path = os.path.join(SCREENSHOTS_DIR, "03_quiz_player.png")
        page.screenshot(path=player_path)
        print(f" [Captured] Quiz Player -> {player_path}")

        # 4. Tutor
        page.goto(f"{FRONTEND_URL}/tutor")
        page.wait_for_timeout(2500)
        tutor_path = os.path.join(SCREENSHOTS_DIR, "04_tutor.png")
        page.screenshot(path=tutor_path)
        print(f" [Captured] Tutor -> {tutor_path}")

        # 5. Concept Map
        page.goto(f"{FRONTEND_URL}/concept-map")
        try:
            page.wait_for_selector("svg, .react-flow, canvas, button:has-text('Study'), div:has-text('Nodes')", timeout=35000)
            page.wait_for_timeout(2000)
        except Exception:
            page.wait_for_timeout(5000)
        cmap_path = os.path.join(SCREENSHOTS_DIR, "05_concept_map.png")
        page.screenshot(path=cmap_path)
        print(f" [Captured] Concept Map -> {cmap_path}")

        # 6. Progress / Learner Analytics
        page.goto(f"{FRONTEND_URL}/learner")
        try:
            page.wait_for_selector("text=Mastery, text=Bayesian, h1, h2", timeout=15000)
            page.wait_for_timeout(2000)
        except Exception:
            page.wait_for_timeout(5000)
        prog_path = os.path.join(SCREENSHOTS_DIR, "06_progress.png")
        page.screenshot(path=prog_path)
        print(f" [Captured] Progress & Mastery -> {prog_path}")

        browser.close()
    print("All screenshots successfully captured!")

if __name__ == "__main__":
    main()
