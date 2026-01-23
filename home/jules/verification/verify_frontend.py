from playwright.sync_api import Page, expect, sync_playwright
import time

def test_frontend(page: Page):
    # Go to the homepage
    page.goto("http://127.0.0.1:8000/")

    # Initial page might be loading
    # Wait for the main page title
    # The title is set dynamically by JS: "Project Explorer - <ProjectName>"
    # Since we are in the root of the repo, project name should be "Context_creator" or similar (parent folder name)
    # But let's just wait for "Project Explorer" to be part of the title

    # Wait for loading to finish (max 30 seconds)
    try:
        expect(page).to_have_title(lambda title: "Project Explorer" in title, timeout=10000)
    except AssertionError:
        print("Timed out waiting for Project Explorer title. Current title:", page.title())
        # If it's still loading, we might see "Building Index..."

    # Take a screenshot
    page.screenshot(path="/home/jules/verification/verification.png")
    print("Screenshot taken.")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            test_frontend(page)
        finally:
            browser.close()
