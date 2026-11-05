import { test, expect } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import { mockApi, userId, vacancyId } from './fixtures'
import { logout, navigateTo, noOverflow } from './helpers'

function seedResume(state: Awaited<ReturnType<typeof mockApi>>) {
  state.resumes.push({ id: userId, user_id: userId, file_url: 'http://minio/resumes/anna.docx', embedding: null, created_at: '2026-11-04T10:00:00Z', bytes: Buffer.from('source bytes'), name: 'anna.docx' })
}

test('empty workspace uploads original and returns with it selected', async ({ page }) => {
  const state = await mockApi(page)
  await page.goto('/workspace')
  await page.getByRole('link', { name: 'Загрузить резюме', exact: true }).click()
  await page.getByLabel('Файл резюме').setInputFiles({ name: 'original.docx', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', buffer: await readFile(new URL('../fixtures/resume.docx', import.meta.url)) })
  await page.getByRole('button', { name: 'Загрузить резюме', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  await expect(page.locator('.source-document')).toContainText('original.docx')
  await page.getByLabel('Полный текст вакансии').fill('Python developer')
  await page.getByRole('button', { name: 'Создать версию', exact: true }).click()
  await expect(page.getByLabel('Адаптированный текст резюме')).toBeVisible()
  expect(state.adaptations[0].resume_id).toBe(state.resumes[0].id)
})

test('workspace creates vacancy once, polls and shows copied result plus tab history', async ({ page }, testInfo) => {
  const state = await mockApi(page)
  seedResume(state)
  state.pollsUntilDone = 100
  await page.goto('/workspace')
  const text = 'Python-разработчик\nFastAPI и PostgreSQL'
  await page.getByLabel('Полный текст вакансии').fill(text)
  await page.getByRole('button', { name: 'Создать версию', exact: true }).click()
  await expect(page.getByText('Задача в очереди', { exact: true })).toBeVisible()
  state.pollsUntilDone = 0
  await expect(page.getByLabel('Адаптированный текст резюме')).toHaveValue(/Анна Смирнова/, { timeout: 10000 })
  expect(state.posts).toBe(1)
  expect(state.adaptationPosts).toBe(1)
  expect(state.vacancies[0].text).toBe(text)
  await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.getByRole('button', { name: 'Скопировать текст' }).click()
  await expect(page.getByRole('status')).toContainText(/Текст скопирован|Текст выделен/)
  await noOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('adaptation-result.png'), fullPage: true })
  await navigateTo(page, 'Мои версии')
  await expect(page.locator('.version-row')).toHaveCount(1)
  await page.reload()
  await expect(page.locator('.version-row')).toHaveCount(0)
})

test('existing saved vacancy does not post another vacancy', async ({ page }) => {
  const state = await mockApi(page)
  seedResume(state)
  state.vacancies.push({ id: vacancyId, user_id: userId, text: 'Saved Python vacancy' })
  await page.goto(`/my-vacancies/${vacancyId}`)
  await page.getByRole('link', { name: 'Адаптировать резюме' }).click()
  await expect(page.getByLabel('Полный текст вакансии')).toHaveValue('Saved Python vacancy')
  await page.getByRole('button', { name: 'Создать версию', exact: true }).click()
  await expect(page.getByLabel('Адаптированный текст резюме')).toBeVisible()
  expect(state.posts).toBe(0)
  expect(state.adaptationPosts).toBe(1)
})

test('Critic rejection remains completed result with visible issues', async ({ page }) => {
  const state = await mockApi(page)
  seedResume(state)
  state.reviewPassed = false
  await page.goto('/workspace')
  await page.getByLabel('Полный текст вакансии').fill('Python')
  await page.getByRole('button', { name: 'Создать версию', exact: true }).click()
  await expect(page.getByLabel('Адаптированный текст резюме')).toBeVisible()
  await expect(page.locator('.result-review')).toContainText('Уберите неподтверждённый опыт Docker.')
  expect(state.adaptations[0].status).toBe('done')
})

test('technical failure offers new attempt for existing vacancy', async ({ page }) => {
  const state = await mockApi(page)
  seedResume(state)
  state.failAdaptation = true
  await page.goto('/workspace')
  await page.getByLabel('Полный текст вакансии').fill('Python')
  await page.getByRole('button', { name: 'Создать версию', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('техническая ошибка')
  await expect(page.getByLabel('Адаптированный текст резюме')).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'создать новую попытку' })).toHaveAttribute('href', `/workspace?vacancy=${vacancyId}`)
})

test('uncertain creation blocks duplicate posts and keeps vacancy text', async ({ page }) => {
  const state = await mockApi(page)
  seedResume(state)
  state.adaptationStatus = 500
  await page.goto('/workspace')
  await page.getByLabel('Полный текст вакансии').fill('Python original vacancy')
  await page.getByRole('button', { name: 'Создать версию', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('Сервер мог принять задачу')
  await expect(page.getByRole('button', { name: 'Создать версию', exact: true })).toBeDisabled()
  await expect(page.getByLabel('Полный текст вакансии')).toHaveValue('Python original vacancy')
  expect(state.posts).toBe(1)
  expect(state.adaptationPosts).toBe(1)
})

test('logout during adaptation POST prevents late navigation and private history', async ({ page }) => {
  const state = await mockApi(page)
  seedResume(state)
  state.adaptationDelay = 1000
  await page.goto('/workspace')
  await page.getByLabel('Полный текст вакансии').fill('Private vacancy')
  const requested = page.waitForRequest('**/adaptations')
  await page.getByRole('button', { name: 'Создать версию', exact: true }).click()
  await requested
  await logout(page)
  await page.waitForTimeout(1200)
  await expect(page).toHaveURL(/\/$/)
  await expect(page.locator('.result-document')).toHaveCount(0)
  await expect(page.getByLabel('Полный текст вакансии')).toHaveCount(0)
  expect(await page.evaluate(() => sessionStorage.getItem('access_token'))).toBeNull()
})

test('successful delayed creation remains discoverable after navigating away', async ({ page }) => {
  const state = await mockApi(page)
  seedResume(state)
  state.adaptationDelay = 1600
  await page.goto('/workspace')
  await page.getByLabel('Полный текст вакансии').fill('Python')
  const requested = page.waitForRequest('**/adaptations')
  await page.getByRole('button', { name: 'Создать версию', exact: true }).click()
  await requested
  await navigateTo(page, 'Мои версии')
  await expect(page.locator('.version-row')).toHaveCount(1)
  await expect(page).toHaveURL(/\/my-versions$/)
  await page.locator('.version-row').click()
  await expect(page.getByLabel('Адаптированный текст резюме')).toBeVisible()
  expect(state.adaptationPosts).toBe(1)
})

test('changing source preserves existing vacancy and does not create a duplicate', async ({ page }) => {
  const state = await mockApi(page)
  seedResume(state)
  state.vacancies.push({ id: vacancyId, user_id: userId, text: 'Saved Python vacancy' })
  await page.goto(`/workspace?vacancy=${vacancyId}`)
  await expect(page.getByLabel('Полный текст вакансии')).toHaveValue('Saved Python vacancy')
  await page.getByRole('link', { name: 'Загрузить другое' }).click()
  await page.getByLabel('Файл резюме').setInputFiles({ name: 'replacement.docx', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', buffer: await readFile(new URL('../fixtures/resume.docx', import.meta.url)) })
  await page.getByRole('button', { name: 'Загрузить резюме', exact: true }).click()
  await expect(page).toHaveURL(/\/workspace$/)
  await expect(page.getByLabel('Полный текст вакансии')).toHaveValue('Saved Python vacancy')
  await page.getByRole('button', { name: 'Создать версию', exact: true }).click()
  await expect(page.getByLabel('Адаптированный текст резюме')).toBeVisible()
  expect(state.vacancies).toHaveLength(1)
  expect(state.posts).toBe(1)
  expect(state.adaptations[0].resume_id).toBe(state.resumes[1].id)
  expect(state.adaptations[0].vacancy_id).toBe(vacancyId)
})
