import { test, expect } from '@playwright/test';
test.describe('UI Redesign Visual Regression', () => {
  test('should render app shell', async ({ page }) => { await page.goto('http://localhost:3000'); await expect(page.locator('.app-shell')).toBeVisible(); });
});
