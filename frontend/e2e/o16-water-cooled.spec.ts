import { test, expect } from '@playwright/test';

test.describe('O16 water-cooled head pressure', () => {
  test('dashboard states, recommendation, safety, and no fake LIVE', async ({ page }) => {
    await page.goto('/agents/variable-speed/water-cooled-head-pressure');
    await expect(page.locator('body')).toContainText(/O16/);
    await expect(page.locator('body')).toContainText(/Variable Head Pressure Control/i);
    await expect(page.locator('body')).toContainText(/Water-Cooled/i);
    await expect(page.locator('body')).toContainText(/BMS CONNECTED|BMS OFFLINE/);
    await expect(page.locator('body')).toContainText(/Engineering Recommendation/i);
    await expect(page.locator('body')).toContainText(/Safety & Control Envelope/i);
    await expect(page.locator('body')).toContainText(/SAFE MODE/);
    await expect(page.locator('body')).not.toContainText(/\bundefined\b/);
    await expect(page.locator('body')).not.toContainText(/\bNaN\b/);
    const text = await page.locator('body').innerText();
    if (/SIMULATION|SIMULATED/.test(text)) {
      expect(text).not.toMatch(/SIMULATION[\s\S]{0,80}BMS CONNECTED/);
      expect(text).not.toMatch(/SIMULATED[\s\S]{0,40}LIVE/);
    }
  });
});
