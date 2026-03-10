import { expect, test } from '@playwright/test'

test('Agent 面板可展示 review 失败的 detail 文案', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('nav-agent').click()

  await page.getByTestId('task-mode-simple').click()
  await page.getByTestId('task-type-select').selectOption('competition_eligibility_check')
  await page.getByTestId('eligibility-competition-query-input').fill('10')
  await page.getByTestId('eligibility-manual-competition-id').fill('10')
  await page.getByTestId('eligibility-grade-select').selectOption('sophomore')
  await page.getByTestId('eligibility-achievements-input').fill('robotics, control, testing')
  await page.getByTestId('eligibility-prerequisites-input').fill('需要确认硬件调试条件')
  await page.getByTestId('eligibility-team-mode-select').selectOption('team')
  await page.getByTestId('eligibility-notes-input').fill('用于验证 review 失败提示')

  await page.getByTestId('task-submit-button').click()
  await expect
    .poll(async () => (await page.getByTestId('run-status-status').textContent())?.trim() ?? '', {
      timeout: 30_000,
    })
    .toContain('待审核')

  await page.route('**/api/agent/tasks/*/review', async (route) => {
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Review is only available for awaiting_review tasks.' }),
    })
  })

  page.once('dialog', async (dialog) => {
    await dialog.accept('浏览器 smoke：验证 detail 展示')
  })
  await page.getByTestId('run-action-review-reject').click()
  await expect(page.getByTestId('run-status-network-error')).toContainText(
    'Review is only available for awaiting_review tasks.',
  )
})
