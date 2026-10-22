from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    page = b.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://localhost:5173/login")
    page.locator("button:has-text('Continue as Demo Student')").click()
    page.wait_for_timeout(2500)
    page.evaluate("""() => {
        localStorage.setItem("studymind_active_course", "a091a4aa-a333-4a0c-85ec-9af9ad8505bd");
        localStorage.setItem("studymind_active_course_e5ee47b2-ad1d-4536-b3eb-a165de1792b1", "a091a4aa-a333-4a0c-85ec-9af9ad8505bd");
    }""")
    page.goto("http://localhost:5173/dashboard")
    page.wait_for_timeout(2500)
    page.locator("button:has-text('Concept Map')").first.click()
    # Wait for the concept map network request and render
    page.wait_for_timeout(32000)
    page.screenshot(path="artifacts/screenshots/05_concept_map.png")
    print("Concept Map captured successfully!")
    b.close()
