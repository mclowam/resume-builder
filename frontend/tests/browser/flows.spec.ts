import { test, expect } from '@playwright/test'
import { readFile } from 'node:fs/promises'

import { mockApi, userId, missingId } from './fixtures'
import { login, noOverflow, navigateTo, logout, openNavigation } from './helpers'

test('registration, login, PDF/DOCX upload, authorized download, profile and logout', async ({ page }, testInfo) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await mockApi(page, 'anonymous')
  await page.goto('/')
  await expect(page.locator('main')).toBeEmpty()
  await page.getByRole('link', { name: 'Регистрация', exact: true }).click()
  await page.getByLabel('Имя пользователя').fill('browser-test')
  await page.getByLabel('Пароль', { exact: true }).fill('browser-password')
  await page.getByRole('button', { name: 'Зарегистрироваться' }).click()
  await expect(page.getByRole('status')).toContainText('Аккаунт создан')
  await page.getByRole('link', { name: 'Перейти ко входу' }).click()
  await login(page)
  await expect(page.getByRole('heading', { name: 'Пока нет резюме' })).toBeVisible()
  for (const name of ['resume.pdf', 'резюме.docx']) {
    await page.getByRole('link', { name: 'Добавить резюме' }).click()
    const file = new URL(`../fixtures/${name.endsWith('.pdf') ? 'resume.pdf' : 'resume.docx'}`, import.meta.url)
    const bytes = await readFile(file)
    await page.getByLabel('Файл резюме').setInputFiles({ name, mimeType: name.endsWith('.pdf') ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', buffer: bytes })
    await page.getByRole('button', { name: 'Загрузить резюме' }).click()
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: `Скачать ${name}`, exact: true }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe(name)
    expect(await readFile((await download.path())!)).toEqual(bytes)
    await expect(page.getByRole('status').filter({ hasText: 'передан браузеру' })).toBeVisible()
  }
  await noOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('resumes.png'), fullPage: true })
  await navigateTo(page, 'Профиль')
  await expect(page.locator('dd').filter({ hasText: 'browser-test' })).toBeVisible()
  await expect(page.locator('a[href="/users"]')).toHaveCount(0)
  await logout(page)
  await expect(page.locator('main')).toBeEmpty()
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Войдите в аккаунт' })).toBeVisible()
  await expect(page.locator('dd')).toHaveCount(0)
  expect(errors).toEqual([])
})

test('vacancy validation, uncertain POST keeps text, creation, list and safe full text', async ({ page }, testInfo) => {
  const state = await mockApi(page)
  await page.goto('/my-vacancies')
  await expect(page.getByRole('heading', { name: 'Пока нет вакансий' })).toBeVisible()
  await page.getByRole('link', { name: 'Добавить вакансию' }).click()
  await page.getByLabel('Полный текст вакансии').fill('   ')
  await page.getByRole('button', { name: 'Сохранить вакансию' }).click()
  await expect(page.getByRole('alert')).toContainText('Введите полный текст')
  expect(state.posts).toBe(0)
  const text = 'Frontend developer\n\nПолный текст вакансии: React и TypeScript.\n<script>window.injected = true</script>\n' + 'ОченьДлинноеСлово'.repeat(25)
  await page.getByLabel('Полный текст вакансии').fill(text)
  state.postStatus = 500
  await page.getByRole('button', { name: 'Сохранить вакансию' }).click()
  await expect(page.getByRole('alert')).toContainText('Сервер мог сохранить данные')
  await expect(page.getByLabel('Полный текст вакансии')).toHaveValue(text)
  expect(state.posts).toBe(1)
  state.postStatus = 0
  await page.getByRole('button', { name: 'Сохранить вакансию' }).click()
  await expect(page.locator('.full-text')).toHaveText(text)
  expect(await page.evaluate(() => 'injected' in window)).toBe(false)
  await page.reload()
  await expect(page.locator('.full-text')).toHaveText(text)
  await noOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('vacancy.png'), fullPage: true })
  await page.getByRole('link', { name: 'Назад: Мои вакансии' }).click()
  await expect(page.locator('.text-preview')).toHaveText(text)
  await page.getByRole('link', { name: 'Открыть', exact: true }).click()
  await expect(page.locator('.full-text')).toHaveText(text)
})

test('invalid file, server 422, missing downloads, network failure and retry', async ({ page }) => {
  const state = await mockApi(page)
  await page.goto('/add-resume')
  await page.getByLabel('Файл резюме').setInputFiles({ name: 'wrong.txt', mimeType: 'text/plain', buffer: Buffer.from('wrong') })
  await page.getByRole('button', { name: 'Загрузить резюме' }).click()
  await expect(page.getByRole('alert')).toContainText('Выберите непустой файл PDF или DOCX')
  expect(state.posts).toBe(0)
  state.postStatus = 422
  await page.getByLabel('Файл резюме').setInputFiles({ name: 'broken.pdf', mimeType: 'application/pdf', buffer: Buffer.from('broken') })
  await page.getByRole('button', { name: 'Загрузить резюме' }).click()
  await expect(page.getByRole('alert')).toContainText('Нужен корректный')
  await expect(page.locator('.selected-file')).toContainText('broken.pdf')
  state.resumes.push({ id: userId, user_id: userId, file_url: 'http://minio:9000/key/resume.pdf', embedding: null, created_at: '2026-10-25T10:00:00Z', bytes: Buffer.from('pdf'), name: 'resume.pdf' })
  await navigateTo(page, 'Мои резюме')
  await expect(page.getByRole('heading', { name: 'resume.pdf' })).toBeVisible()
  state.resumes.length = 0
  await page.getByRole('button', { name: 'Скачать resume.pdf' }).click()
  await expect(page.getByRole('alert')).toContainText('Не найдено')
  state.offline = true
  await page.getByRole('button', { name: 'Обновить список' }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'Нет связи' })).toBeVisible()
  state.offline = false
  await page.getByRole('button', { name: 'Повторить', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Пока нет резюме' })).toBeVisible()
})

test('protected deep links, allowed login return, unknown URL and resource 404', async ({ page }) => {
  await mockApi(page, 'anonymous')
  await page.goto(`/my-vacancies/${missingId}`)
  await expect(page.getByRole('heading', { name: 'Войдите в аккаунт' })).toBeVisible()
  await page.getByRole('link', { name: 'Войти', exact: true }).click()
  await login(page)
  await expect(page).toHaveURL(new RegExp(`/my-vacancies/${missingId}$`))
  await expect(page.getByRole('alert')).toContainText('Не найдено')
  await page.goto(`/users/${missingId}`)
  await expect(page.getByRole('heading', { name: 'Доступ ограничен' })).toBeVisible()
  await page.goto('/unknown')
  await expect(page.getByRole('heading', { name: 'Страница не найдена' })).toBeVisible()
  await logout(page)
  await page.goto('/login?next=https://evil.invalid')
  await login(page)
  await expect(page).toHaveURL(/\/my-resumes$/)
})

test('restoration refresh success and failed refresh 500 lead to login', async ({ page }) => {
  const state = await mockApi(page)
  state.expired = true
  await page.goto('/profile')
  await expect(page.locator('dd').filter({ hasText: 'browser-test' })).toBeVisible()
  expect(state.refreshes).toBe(1)
  state.expired = true
  state.refreshFailure = true
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Войдите в аккаунт' })).toBeVisible()
  await expect(page.getByRole('status')).toContainText('Не удалось восстановить сессию')
  expect(state.refreshes).toBe(2)
  expect(await page.evaluate(() => sessionStorage.getItem('access_token'))).toBeNull()
  await page.getByRole('link', { name: 'Войти', exact: true }).click()
  await expect(page.getByLabel('Пароль', { exact: true })).toBeVisible()
})

test('logout during refresh does not resurrect private data', async ({ page }) => {
  const state = await mockApi(page)
  await page.goto('/my-resumes')
  await expect(page.getByRole('heading', { name: 'Пока нет резюме' })).toBeVisible()
  state.expired = true
  state.refreshDelay = 700
  const refreshing = page.waitForRequest('**/auth/refresh')
  await page.getByRole('button', { name: 'Обновить список' }).click()
  await refreshing
  await logout(page)
  await page.waitForTimeout(900)
  await expect(page.locator('main')).toBeEmpty()
  expect(await page.evaluate(() => sessionStorage.getItem('access_token'))).toBeNull()
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Войдите в аккаунт' })).toBeVisible()
})

test('draft survives failed refresh for the same user and explicit logout clears it', async ({ page }) => {
  const state = await mockApi(page)
  await page.goto('/add-vacancy')
  await page.getByLabel('Полный текст вакансии').fill('Мой несохранённый текст')
  state.expired = true
  state.refreshFailure = true
  await page.getByRole('button', { name: 'Сохранить вакансию' }).click()
  await expect(page.getByRole('heading', { name: 'Войдите в аккаунт' })).toBeVisible()
  state.expired = false
  state.refreshFailure = false
  await page.getByRole('link', { name: 'Войти', exact: true }).click()
  await login(page)
  await expect(page.getByLabel('Полный текст вакансии')).toHaveValue('Мой несохранённый текст')
  await logout(page)
  await page.getByRole('link', { name: 'Вход', exact: true }).click()
  await login(page)
  await navigateTo(page, 'Мои вакансии')
  await page.getByRole('link', { name: 'Добавить вакансию', exact: true }).click()
  await expect(page.getByLabel('Полный текст вакансии')).toHaveValue('')
})

test('400, 403, 422 preserve input; empty users and keyboard navigation', async ({ page }) => {
  const state = await mockApi(page, 'staff')
  await page.goto('/add-vacancy')
  await page.getByLabel('Полный текст вакансии').fill('Полный текст')
  for (const status of [400, 403, 422]) {
    state.postStatus = status
    await page.getByRole('button', { name: 'Сохранить вакансию' }).click()
    await expect(page.getByRole('alert')).toBeVisible()
    await expect(page.getByLabel('Полный текст вакансии')).toHaveValue('Полный текст')
  }
  expect(state.posts).toBe(3)
  state.postDelay = 500
  await page.locator('form').evaluate((element) => {
    const form = element as HTMLFormElement
    form.requestSubmit()
    form.requestSubmit()
  })
  await expect(page.getByRole('button', { name: 'Сохранение…' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Сохранить вакансию' })).toBeEnabled()
  expect(state.posts).toBe(4)
  state.emptyUsers = true
  await navigateTo(page, 'Пользователи')
  await expect(page.getByRole('heading', { name: 'Пользователи не найдены' })).toBeVisible()
  await openNavigation(page)
  await page.getByRole('link', { name: 'Пользователи', exact: true }).focus()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Профиль', exact: true })).toBeFocused()
  expect(await page.getByRole('link', { name: 'Профиль', exact: true }).evaluate((element) => getComputedStyle(element).outlineStyle)).not.toBe('none')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Профиль', exact: true })).toBeVisible()
  await noOverflow(page)
})

test('staff list, detail, reload and browser history remain available', async ({ page }) => {
  await mockApi(page, 'staff')
  await page.goto('/my-resumes')
  await expect(page.getByRole('heading', { name: 'Мои резюме', exact: true })).toBeVisible()
  await navigateTo(page, 'Пользователи')
  await page.getByRole('link', { name: 'browser-test', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Пользователь', exact: true })).toBeVisible()
  await page.reload()
  await expect(page.locator('dd').filter({ hasText: 'browser-test' })).toBeVisible()
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Пользователи', exact: true })).toBeVisible()
  await page.goForward()
  await expect(page.getByRole('heading', { name: 'Пользователь', exact: true })).toBeVisible()
  await logout(page)
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Войдите в аккаунт' })).toBeVisible()
  await expect(page.locator('dd')).toHaveCount(0)
})
