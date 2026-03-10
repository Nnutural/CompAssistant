import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { expect, test } from '@playwright/test'

interface DemoCase {
  case_id: string
  task_type: string
  mode: string
  input: {
    direction?: string
    grade?: string
    abilities?: string
    preference_tags?: string
    extra_notes?: string
  }
}

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const fixturePath = path.resolve(currentDir, './fixtures/agent-demo-cases.json')
const fixtures = JSON.parse(fs.readFileSync(fixturePath, 'utf-8')) as DemoCase[]
const recommendationCase = fixtures.find((item) => item.case_id === 'recommendation-001')

if (!recommendationCase) {
  throw new Error('Missing recommendation-001 fixture.')
}

test('Agent 面板 recommendation happy path smoke', async ({ page }) => {
  await page.goto('/')

  await page.getByTestId('nav-agent').click()
  await expect(page.getByTestId('agent-panel-view')).toBeVisible()

  await page.getByTestId('task-mode-simple').click()
  await page.getByTestId('task-type-select').selectOption(recommendationCase.task_type)
  await page.getByTestId('recommendation-direction-input').fill(recommendationCase.input.direction ?? '')
  if (recommendationCase.input.grade) {
    await page.getByTestId('recommendation-grade-select').selectOption(recommendationCase.input.grade)
  }
  await page.getByTestId('recommendation-abilities-input').fill(recommendationCase.input.abilities ?? '')
  await page.getByTestId('recommendation-preferences-input').fill(recommendationCase.input.preference_tags ?? '')
  await page.getByTestId('recommendation-notes-input').fill(recommendationCase.input.extra_notes ?? '')

  await expect(page.getByTestId('simple-objective-preview')).toContainText('推荐')
  await expect(page.getByTestId('simple-payload-preview')).toContainText('"ability_tags"')

  await page.getByTestId('task-mode-advanced').click()
  const advancedPayloadEditor = page.getByTestId('advanced-payload-editor')
  await expect(advancedPayloadEditor).toBeEditable()
  await expect
    .poll(() => advancedPayloadEditor.inputValue(), { timeout: 15_000 })
    .toContain('"profile"')

  await page.getByTestId('task-submit-button').click()

  await expect(page.getByTestId('run-status-card')).toBeVisible()
  await expect(page.getByTestId('event-timeline-card')).toBeVisible()
  const sourceRunId = (await page.getByTestId('run-status-run-id').textContent())?.trim() ?? ''
  expect(sourceRunId).not.toEqual('')

  await expect(page.getByTestId('event-timeline-list')).toBeVisible()
  await expect
    .poll(() => page.getByTestId('artifact-item').count(), { timeout: 30_000 })
    .toBeGreaterThan(0)

  await page.getByTestId('task-history-refresh').click()
  await expect(page.getByTestId('task-history-list')).toContainText(sourceRunId)

  await expect(page.getByTestId('run-action-retry')).toBeVisible()
  await page.getByTestId('run-action-retry').click()
  await expect
    .poll(async () => (await page.getByTestId('run-status-run-id').textContent())?.trim() ?? '', {
      timeout: 20_000,
    })
    .not.toBe(sourceRunId)

  await page.getByTestId('nav-competitions').click()
  await expect(page.getByTestId('competitions-view')).toBeVisible()
})
