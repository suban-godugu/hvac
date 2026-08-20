import { test, expect } from '@playwright/test';

test.describe('O15 air-cooled head pressure', () => {
  test('dashboard states and engineering panels', async ({ page }) => {
    await page.goto('/agents/variable-speed/air-cooled-head-pressure');
    await expect(page.locator('body')).toContainText(/O15/);
    await expect(page.locator('body')).toContainText(/Variable Head Pressure Control/i);
    await expect(page.locator('body')).toContainText(/Air-Cooled/i);
    await expect(page.locator('body')).toContainText(/BMS OFFLINE|BMS LIVE/);
    await expect(page.locator('body')).toContainText(/O15 Optimization Recommendation/i);
    await expect(page.locator('body')).toContainText(/Why this recommendation/i);
    await expect(page.locator('body')).toContainText(/Safety & Control Envelope/i);
    await expect(page.locator('body')).toContainText(/Outdoor Air/);
    await expect(page.locator('body')).not.toContainText(/SIMULATION data as LIVE/i);
    await expect(page.locator('body')).not.toContainText(/\bundefined\b/);
    await expect(page.locator('body')).not.toContainText(/\bNaN\b/);
  });
});
