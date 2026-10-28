import { test, expect } from '@playwright/test'
import { mockApi, userId, vacancyId } from './fixtures'
import { noOverflow, openNavigation } from './helpers'

test('guest pages and form focus', async ({ page }, testInfo) => {
  await mockApi(page, 'anonymous')
  for (const path of ['login', 'register']) {
    await page.goto(`/${path}`)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await page.getByLabel('Имя пользователя').focus()
    await expect(page.getByLabel('Имя пользователя')).toBeFocused()
    await noOverflow(page)
    await page.screenshot({ path: testInfo.outputPath(`${path}.png`), fullPage: true, animations: 'disabled' })
  }
})

test('documents, profile, navigation and states at each viewport', async ({ page }, testInfo) => {
  const state = await mockApi(page)
  state.profile.username = 'Александра_Константинопольская_оченьдлинноеимя'
  state.resumes.push({ id: userId, user_id: userId, file_url: 'http://minio/resumes/Frontend_разработчик_Александра_Константинопольская.pdf', embedding: null, created_at: '2026-10-25T10:00:00Z', bytes: Buffer.from('pdf'), name: 'resume.pdf' })
  state.vacancies.push({ id: vacancyId, user_id: userId, text: 'Frontend-разработчик\n\nМы создаём удобные инструменты для работы с документами. Ищем разработчика, который умеет превращать сложные задачи в понятные интерфейсы.\n\nЧем предстоит заниматься\nРазрабатывать интерфейсы на React и TypeScript. Работать вместе с дизайнерами и backend-командой.\n\nЧто мы предлагаем\nУдалённая работа, гибкий график и внимательное отношение к качеству.\n\n' + 'ОченьДлинноеСлово'.repeat(12) })
  for (const [name, path] of [
    ['resumes', '/my-resumes?created=1'],
    ['add-resume', '/add-resume'],
    ['vacancies', '/my-vacancies'],
    ['add-vacancy', '/add-vacancy'],
    ['vacancy', `/my-vacancies/${vacancyId}`],
    ['profile', '/profile'],
    ['forbidden', '/users'],
    ['not-found', '/unknown'],
  ]) {
    await page.goto(path)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await expect(page.getByRole('status').filter({ hasText: 'Загрузка' })).toHaveCount(0)
    if (name === 'profile') await expect(page.locator('.details')).toBeVisible()
    if (name === 'resumes' || name === 'vacancies') await expect(page.locator('.resource-list')).toBeVisible()
    if (name === 'vacancy') await expect(page.locator('.full-text')).toHaveText(state.vacancies[0].text)
    await noOverflow(page)
    await page.screenshot({ path: testInfo.outputPath(`${name}.png`), fullPage: true, animations: 'disabled' })
  }
  await openNavigation(page)
  await expect(page.locator('a[href="/users"]')).toHaveCount(0)
  await page.screenshot({ path: testInfo.outputPath('nonstaff-navigation.png'), fullPage: true, animations: 'disabled' })
  if (await page.getByRole('dialog').isVisible()) await page.keyboard.press('Escape')
  state.resumes.length = 0
  await page.goto('/my-resumes')
  await expect(page.getByRole('heading', { name: 'Пока нет резюме' })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('empty.png'), fullPage: true, animations: 'disabled' })
  state.offline = true
  await page.getByRole('button', { name: 'Обновить список' }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await noOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('error.png'), fullPage: true, animations: 'disabled' })
})

test('staff list, detail and navigation at each viewport', async ({ page }, testInfo) => {
  const state = await mockApi(page, 'staff')
  state.profile.username = 'Сотрудник_с_длинным_именем_пользователя'
  await page.goto('/users')
  await expect(page.locator('.resource-list')).toContainText(state.profile.username)
  await noOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('users.png'), fullPage: true, animations: 'disabled' })
  await openNavigation(page)
  await expect(page.getByRole('navigation', { name: 'Основная навигация' }).getByRole('link', { name: 'Пользователи' })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('staff-navigation.png'), fullPage: true, animations: 'disabled' })
  if (await page.getByRole('dialog').isVisible()) await page.keyboard.press('Escape')
  await page.getByRole('link', { name: 'Открыть', exact: true }).click()
  await expect(page.locator('.details')).toContainText(state.profile.username)
  await noOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('user.png'), fullPage: true, animations: 'disabled' })
})
