import { expect, test } from "@playwright/test";
const telemetryTimeout = 15000;
test("health returns the REST envelope and an open file source", async ({ request }) => {
  await expect(async () => {
    const response = await request.get("/api/health");
    expect(response.status()).toBe(200);
    const envelope = await response.json();
    expect(Object.keys(envelope).sort()).toEqual(["data", "error", "success"]);
    expect(envelope).toMatchObject({
      success: true, error: null, data: { status: "ok", camera_open: true },
    });
  }).toPass({ timeout: telemetryTimeout });
});


test('guided flow connects and advances frames with no face', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /take a look/ })).toBeVisible();
  await page.getByRole('button', { name: 'Start analyzing' }).click();
  await expect(page).toHaveURL(/#camera$/);
  await expect(page.getByRole('navigation', { name: 'Analysis progress' }).locator('[aria-current="step"]')).toContainText('Camera');
  await expect(page.getByText(/Camera connected/).first()).toBeVisible({ timeout: telemetryTimeout });
  await expect(page.getByText(/No face detected/).first()).toBeVisible({ timeout: telemetryTimeout });
  await expect(page.getByRole('button', { name: 'Analyze my skin' })).toBeDisabled();
  const wrapper = page.locator('[data-frame-id]');
  await expect(wrapper).toBeVisible({ timeout: telemetryTimeout });
  const initial = Number(await wrapper.getAttribute('data-frame-id'));
  await expect.poll(async () => Number(await wrapper.getAttribute('data-frame-id')), { timeout: telemetryTimeout }).toBeGreaterThan(initial);
});
test('reset rejects a foreign Origin', async ({ request }) => {
  const response = await request.post('/api/reset', { headers: { Origin: 'http://evil.example' } });
  expect(response.status()).toBe(403);
  expect(await response.json()).toMatchObject({ success: false, data: null });
});
