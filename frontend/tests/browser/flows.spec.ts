import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { readFile } from 'node:fs/promises'

const userId = '11111111-1111-4111-8111-111111111111'
const vacancyId = '22222222-2222-4222-8222-222222222222'
const missingId = '99999999-9999-4999-8999-999999999999'
const profile = { user_id: userId, username: 'browser-test', is_staff: false }
const tokens = { access_token: 'test-access', refresh_token: 'test-refresh', token_type: 'bearer' }

async function mockApi(page: Page, authenticated = true) {
  const state = {
    resumes: [] as { id: string; user_id: string; file_url: string; embedding: null; created_at: string; bytes: Buffer; name: string }[],
    vacancies: [] as { id: string; user_id: string; text: string }[],
    expired: false,
    refreshFailure: false,
    offline: false,
    postStatus: 0,
    refreshes: 0,
    posts: 0,
    refreshDelay: 0,
    emptyUsers: false,
    postDelay: 0,
  }
  if (authenticated) await page.addInitScript((value) => {
    if (!sessionStorage.getItem('test-seeded')) {
      sessionStorage.setItem('access_token', value.access_token)
      sessionStorage.setItem('refresh_token', value.refresh_token)
      sessionStorage.setItem('test-seeded', 'true')
    }
  }, tokens)
  await page.route(/\/(auth|resumes|vacancies)(\/|$)/, async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    const respond = (body: unknown, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
    if (state.offline) return route.abort('connectionrefused')
    if (path === '/auth/register') return respond({ user_id: userId, username: profile.username }, 201)
    if (path === '/auth/login') return respond(tokens)
    if (path === '/auth/refresh') {
      state.refreshes++
      if (state.refreshDelay) await new Promise((resolve) => setTimeout(resolve, state.refreshDelay))
      if (state.refreshFailure) return respond({}, 500)
      state.expired = false
      return respond({ ...tokens, access_token: 'refreshed-access' })
    }
    if (!request.headers().authorization || state.expired) return respond({}, 401)
    if (path === '/auth/me') return respond(profile)
    if (path === '/auth/users') return respond(state.emptyUsers ? [] : [{ ...profile, is_active: true }])
    if (path === `/auth/users/${userId}`) return respond({ ...profile, is_active: true })
    if (path === '/resumes' && request.method() === 'POST') {
      state.posts++
      if (state.postDelay) await new Promise((resolve) => setTimeout(resolve, state.postDelay))
      if (state.postStatus) return respond({}, state.postStatus)
      const body = request.postDataBuffer()!
      const name = body.toString('utf8').match(/filename="([^"]+)"/)?.[1] || 'resume.pdf'
      const start = body.indexOf('\r\n\r\n') + 4
      const boundary = request.headers()['content-type'].split('boundary=')[1]
      const end = body.indexOf(`\r\n--${boundary}`, start)
      const id = `${state.resumes.length + 3}3333333-3333-4333-8333-333333333333`
      state.resumes.push({ id, user_id: userId, file_url: `http://minio:9000/resumes/internal/key/${encodeURIComponent(name)}`, embedding: null, created_at: '2026-10-25T10:00:00Z', bytes: body.subarray(start, end), name })
      return route.fulfill({ status: 201, headers: { Location: `http://resume:8000/resumes/${id}` }, body: '' })
    }
    if (path === '/resumes') return respond(state.resumes.map(({ bytes, name, ...resume }) => { void bytes; void name; return resume }))
    if (path.startsWith('/resumes/')) {
      const resume = state.resumes.find((item) => path.endsWith(item.id))
      return resume ? route.fulfill({ status: 200, body: resume.bytes, headers: { 'Content-Type': resume.name.endsWith('.pdf') ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'Content-Disposition': `attachment; filename*=UTF-8''${encodeURIComponent(resume.name)}` } }) : respond({}, 404)
    }
    if (path === '/vacancies' && request.method() === 'POST') {
      state.posts++
      if (state.postDelay) await new Promise((resolve) => setTimeout(resolve, state.postDelay))
      if (state.postStatus) return respond({}, state.postStatus)
      const vacancy = { id: vacancyId, user_id: userId, text: request.postDataJSON().text }
      state.vacancies.push(vacancy)
      return respond(vacancy, 201)
    }
    if (path === '/vacancies') return respond(state.vacancies)
    if (path === `/vacancies/${vacancyId}` && state.vacancies.length) return respond(state.vacancies[0])
    return respond({}, 404)
  })
  return state
}

async function login(page: Page) {
  await page.getByLabel('Имя пользователя').fill('browser-test')
  await page.getByLabel('Пароль', { exact: true }).fill('browser-password')
  await page.getByRole('button', { name: 'Войти', exact: true }).click()
}

async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
}

test('registration, login, PDF/DOCX upload, authorized download, profile, users and logout', async ({ page }, testInfo) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await mockApi(page, false)
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
  await page.getByRole('link', { name: 'Профиль', exact: true }).click()
  await expect(page.locator('dd').filter({ hasText: 'browser-test' })).toBeVisible()
  await page.getByRole('link', { name: 'Пользователи', exact: true }).click()
  await page.getByRole('link', { name: 'browser-test', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Пользователь', exact: true })).toBeVisible()
  await page.reload()
  await expect(page.locator('dd').filter({ hasText: 'browser-test' })).toBeVisible()
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Пользователи', exact: true })).toBeVisible()
  await page.goForward()
  await expect(page.getByRole('heading', { name: 'Пользователь', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Выйти' }).click()
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
  await page.getByRole('link', { name: '← Мои вакансии' }).click()
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
  await page.getByRole('link', { name: 'Мои резюме', exact: true }).click()
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
  await mockApi(page, false)
  await page.goto(`/my-vacancies/${missingId}`)
  await expect(page.getByRole('heading', { name: 'Войдите в аккаунт' })).toBeVisible()
  await page.getByRole('link', { name: 'Войти', exact: true }).click()
  await login(page)
  await expect(page).toHaveURL(new RegExp(`/my-vacancies/${missingId}$`))
  await expect(page.getByRole('alert')).toContainText('Не найдено')
  await page.goto(`/users/${missingId}`)
  await expect(page.getByRole('alert')).toContainText('Не найдено')
  await page.goto('/unknown')
  await expect(page.getByRole('heading', { name: 'Страница не найдена' })).toBeVisible()
  await page.getByRole('button', { name: 'Выйти' }).click()
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
  await page.getByRole('button', { name: 'Выйти' }).click()
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
  await page.getByRole('button', { name: 'Выйти' }).click()
  await page.getByRole('link', { name: 'Вход', exact: true }).click()
  await login(page)
  await page.getByRole('link', { name: 'Мои вакансии', exact: true }).click()
  await page.getByRole('link', { name: 'Добавить вакансию', exact: true }).click()
  await expect(page.getByLabel('Полный текст вакансии')).toHaveValue('')
})

test('400, 403, 422 preserve input; empty users and keyboard navigation', async ({ page }) => {
  const state = await mockApi(page)
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
  await page.getByRole('link', { name: 'Пользователи', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Пользователи не найдены' })).toBeVisible()
  await page.getByRole('link', { name: 'Пользователи', exact: true }).focus()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Профиль', exact: true })).toBeFocused()
  expect(await page.getByRole('link', { name: 'Профиль', exact: true }).evaluate((element) => getComputedStyle(element).outlineStyle)).not.toBe('none')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Профиль', exact: true })).toBeVisible()
  await noOverflow(page)
})
