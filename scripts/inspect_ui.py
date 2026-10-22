from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    page = b.new_page()
    page.goto("http://localhost:5173/login")
    page.wait_for_timeout(1000)
    page.locator("button:has-text('Continue as Demo Student')").click()
    page.wait_for_timeout(2500)
    
    sel = page.locator("select[aria-label='Select active course']")
    print("select visible:", sel.is_visible())
    if sel.is_visible():
        print("options:", sel.locator("option").all_inner_texts())
        print("values:", sel.locator("option").evaluate_all("opts => opts.map(o => o.value)"))
    
    ls = page.evaluate("() => ({ ...localStorage })")
    print("localStorage keys:", list(ls.keys()))
    token_str = ls.get('sb-uhkxfbcltdzvqdmigttx-auth-token', '{}')
    import json
    token_data = json.loads(token_str)
    print("Supabase logged-in user id:", token_data.get('user', {}).get('id'))
    print("Supabase email:", token_data.get('user', {}).get('email'))
    b.close()
