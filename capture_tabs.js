const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

  console.log('Navigating to app...');
  await page.goto('http://localhost:8512', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);

  // Click the Matches radio in the sidebar
  const sidebar = page.locator('section[data-testid="stSidebar"]');
  const matchesRadio = sidebar.locator('label:has-text("Matches")');
  if (await matchesRadio.count() > 0) {
    console.log('Clicking Matches navigation...');
    await matchesRadio.click();
    await page.waitForTimeout(4000);
  } else {
    console.log('Matches radio not found, capturing current state.');
  }

  // Take screenshot of tabs
  const tabList = page.locator('[data-baseweb="tab-list"]');
  if (await tabList.count() > 0) {
    await tabList.screenshot({ path: 'C:/Users/staff/OneDrive/Desktop/Python/Content_Factory/tab_screenshot.png' });
    console.log('Tab screenshot saved to tab_screenshot.png');
  } else {
    await page.screenshot({ path: 'C:/Users/staff/OneDrive/Desktop/Python/Content_Factory/tab_screenshot.png', fullPage: false });
    console.log('Full page screenshot saved (tab-list not found).');
  }

  // Extract computed styles from selected and unselected tabs
  const selectedTab = page.locator('[data-baseweb="tab"][aria-selected="true"]').first();
  const unselectedTab = page.locator('[data-baseweb="tab"][aria-selected="false"]').first();

  console.log('\n========== SELECTED TAB (aria-selected="true") ==========');
  if (await selectedTab.count() > 0) {
    const styles = await selectedTab.evaluate(el => {
      const s = window.getComputedStyle(el);
      return {
        backgroundColor: s.backgroundColor,
        color: s.color,
        fontFamily: s.fontFamily,
        fontWeight: s.fontWeight,
        borderRadius: s.borderRadius,
        padding: s.padding,
      };
    });
    for (const [k, v] of Object.entries(styles)) {
      console.log(`  ${k}: ${v}`);
    }
  }

  console.log('\n========== UNSELECTED TAB (aria-selected="false") ==========');
  if (await unselectedTab.count() > 0) {
    const styles = await unselectedTab.evaluate(el => {
      const s = window.getComputedStyle(el);
      return {
        backgroundColor: s.backgroundColor,
        color: s.color,
        fontFamily: s.fontFamily,
        fontWeight: s.fontWeight,
        borderRadius: s.borderRadius,
        padding: s.padding,
      };
    });
    for (const [k, v] of Object.entries(styles)) {
      console.log(`  ${k}: ${v}`);
    }
  }

  // Also get the tab-list container background
  if (await tabList.count() > 0) {
    const containerBg = await tabList.evaluate(el => window.getComputedStyle(el).backgroundColor);
    console.log(`\n========== TAB LIST CONTAINER ==========`);
    console.log(`  background: ${containerBg}`);
  }

  await browser.close();
  console.log('\nDone.');
})();
