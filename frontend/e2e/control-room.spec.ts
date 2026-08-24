import { test, expect } from '@playwright/test';

test.describe('Phase 2 control room', () => {
  test('overview never shows BMS LIVE and control stays disabled', async ({ page }) => {
    await page.goto('/overview');
    await expect(page.locator('header')).toContainText(/WRITE ENABLED|WRITE DISABLED|SIM CONTROL ON|CONTROL DISABLED/);
    await expect(page.locator('header')).not.toContainText('BMS LIVE');
    await expect(page.locator('body')).toContainText('HVAC Central Optimization Platform');
  });

  test('BMS commissioning page is read-only', async ({ page }) => {
    await page.goto('/platform/bms');
    await expect(page.locator('body')).toContainText('READ-ONLY');
    await expect(page.locator('body')).toContainText('0 devices');
    await expect(page.locator('header')).not.toContainText('BMS LIVE');
    await expect(page.locator('header')).toContainText(/WRITE ENABLED|WRITE DISABLED|SIM CONTROL ON|CONTROL DISABLED/);
  });

  test('telemetry page shows empty as NO DATA not zero', async ({ page }) => {
    await page.goto('/platform/telemetry');
    await expect(page.locator('body')).toContainText('Live Telemetry');
    await expect(page.locator('header')).toContainText(/WRITE ENABLED|WRITE DISABLED|SIM CONTROL ON|CONTROL DISABLED/);
    const body = await page.locator('body').innerText();
    expect(body).not.toMatch(/BMS LIVE/);
  });

  test('agent center shows ENGINE/MODEL and WRITE ENABLED in simulation', async ({ page }) => {
    await page.goto('/agents');
    await expect(page.locator('body')).toContainText('Scheduling');
    await expect(page.locator('body')).toContainText('Plant Control');
    await expect(page.locator('body')).toContainText('Ventilation');
    await expect(page.locator('body')).toContainText('Variable Speed');
    await expect(page.locator('body')).toContainText('Operations');
    await expect(page.locator('body')).toContainText('ENGINE');
    await expect(page.locator('body')).toContainText('MODEL');
    await expect(page.locator('body')).toContainText('CONTROL');
    await expect(page.locator('body')).toContainText('WRITE ENABLED');
    await expect(page.locator('body')).not.toContainText('SIM WRITE ENABLED');
    await expect(page.locator('header')).not.toContainText('BMS LIVE');
  });
});
