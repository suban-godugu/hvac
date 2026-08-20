import { test, expect } from '@playwright/test';

test.describe('HVAC Scheduling & Supervisory Agent Live UI', () => {
  test('should render dashboard and display active opportunities', async ({ page }) => {
    await page.goto('/agents/scheduling');

    // Verify Title & Identity
    await expect(page.locator('h1')).toContainText('Scheduling & Supervisory Agent');
    await expect(page.locator('body')).toContainText('Skyline Corporate Center');

    // Verify Opportunity Studio Cards
    await expect(page.locator('body')).toContainText('Optimum Start/Stop Programming');
    await expect(page.locator('body')).toContainText('Space Temperature Set Points & Control Bands');
    await expect(page.locator('body')).toContainText('Master AHU Supply Air Temperature');
    await expect(page.locator('body')).toContainText('Staging of Chillers & Compressors');

    // Verify Safety Validation Guardrails
    await expect(page.locator('body')).toContainText('Safety Validation Guardrails');
    await expect(page.locator('body')).toContainText('ASHRAE 55 Comfort Envelope');
  });

  test('should navigate to O1 Studio and display thermal trajectory', async ({ page }) => {
    await page.goto('/agents/scheduling/optimum-start-stop');
    await expect(page.locator('h1')).toContainText('Optimum Start/Stop Programming');
    await expect(page.locator('body')).toContainText('Pre-Cooling Thermal Response Trajectory');
    await expect(page.locator('body')).toContainText('Historical Pre-Cooling Calibration Log');
  });

  test('should navigate to O3 Master AHU SAT Studio and show Guideline 36 selector', async ({ page }) => {
    await page.goto('/agents/scheduling/master-ahu-sat');
    await expect(page.locator('h1')).toContainText('Master Air Handling Unit Supply Air Temperature Signal');
    await expect(page.locator('body')).toContainText('Guideline 36 Demand Ranking');
    await expect(page.locator('body')).toContainText('EXCLUDED (PROCESS ROGUE)');
  });

  test('fleet overview is the home landing page', async ({ page }) => {
    await page.goto('/overview');
    await expect(page.locator('body')).toContainText('HVAC Central Optimization Platform');
  });
});
