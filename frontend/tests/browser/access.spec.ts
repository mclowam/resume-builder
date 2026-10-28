import { test, expect } from '@playwright/test'
import { mockApi, userId, missingId } from './fixtures'
import { login, logout, navigateTo, openNavigation, noOverflow } from './helpers'

for (const path of ['/users', `/users/${userId}`, `/users/${missingId}`]) {
  test(`nonstaff cannot request ${path} through direct URL, reload or history`, async ({ page }) => {
    const state = await mockApi(page)
    await page.goto(path)
    await expect(page.getByRole('heading', { name: 'Доступ ограничен' })).toBeVisible()
    await expect(page.locator('a[href="/users"]')).toHaveCount(0)
    await openNavigation(page)
    await expect(page.locator('a[href="/users"]')).toHaveCount(0)
    if (await page.getByRole('dialog').isVisible()) await page.keyboard.press('Escape')
    await page.reload()
    await expect(page.getByRole('heading', { name: 'Доступ ограничен' })).toBeVisible()
    await page.getByRole('link', { name: 'К моим резюме' }).click()
    await expect(page.getByRole('heading', { name: 'Мои резюме', exact: true })).toBeVisible()
    await page.goBack()
    await expect(page.getByRole('heading', { name: 'Доступ ограничен' })).toBeVisible()
    await page.goForward()
    await expect(page.getByRole('heading', { name: 'Мои резюме', exact: true })).toBeVisible()
    await navigateTo(page, 'Профиль')
    await expect(page.locator('dd').filter({ hasText: 'browser-test' })).toBeVisible()
    expect(state.userCalls).toEqual([])
    expect(state.refreshes).toBe(0)
    await noOverflow(page)
  })

  test(`anonymous login return to ${path} respects nonstaff role`, async ({ page }) => {
    const state = await mockApi(page, 'anonymous')
    await page.goto(path)
    await expect(page.getByRole('heading', { name: 'Войдите в аккаунт' })).toBeVisible()
    expect(state.userCalls).toEqual([])
    await page.getByRole('link', { name: 'Войти', exact: true }).click()
    await login(page)
    await expect(page.getByRole('heading', { name: 'Доступ ограничен' })).toBeVisible()
    await expect(page.locator('a[href="/users"]')).toHaveCount(0)
    expect(state.userCalls).toEqual([])
  })
}

for (const role of ['nonstaff', 'staff'] as const) {
  test(`${role} waits for me before showing staff navigation or requesting users`, async ({ page }) => {
    const state = await mockApi(page, role)
    state.meDelay = 800
    await page.addInitScript(() => {
      sessionStorage.setItem('is_staff', 'true')
      sessionStorage.setItem('username', 'admin')
    })
    await page.goto('/users')
    await expect(page.getByRole('status').filter({ hasText: 'Проверка сессии' }).first()).toBeVisible()
    await expect(page.locator('a[href="/users"]')).toHaveCount(0)
    await expect(page.locator('.resource-list')).toHaveCount(0)
    expect(state.userCalls).toEqual([])
    await expect(page.getByRole('heading', { name: role === 'staff' ? 'Пользователи' : 'Доступ ограничен', exact: true })).toBeVisible()
    if (role === 'staff') {
      await expect(page.getByRole('link', { name: 'browser-test', exact: true })).toBeVisible()
      await openNavigation(page)
      await expect(page.getByRole('navigation', { name: 'Основная навигация' }).getByRole('link', { name: 'Пользователи' })).toBeVisible()
      expect(state.userCalls.length).toBeGreaterThan(0)
    } else expect(state.userCalls).toEqual([])
  })
}

for (const path of ['/users', `/users/${userId}`]) {
  test(`server 403 removes already loaded data at ${path} without refresh or logout`, async ({ page }, testInfo) => {
    const state = await mockApi(page, 'staff')
    await page.goto(path)
    await expect(page.locator(path === '/users' ? '.resource-list' : '.details')).toContainText('browser-test')
    state.usersStatus = 403
    await page.getByRole('button', { name: path === '/users' ? 'Обновить список' : 'Обновить профиль' }).click()
    await expect(page.getByRole('heading', { name: 'Доступ ограничен' })).toBeVisible()
    await expect(page.locator('.resource-list, .details')).toHaveCount(0)
    expect(state.refreshes).toBe(0)
    expect(await page.evaluate(() => sessionStorage.getItem('access_token'))).toBe('test-access')
    await noOverflow(page)
    await page.screenshot({ path: testInfo.outputPath('server-forbidden.png'), fullPage: true })
    await navigateTo(page, 'Профиль')
    await expect(page.locator('dd').filter({ hasText: 'browser-test' })).toBeVisible()
  })
}

test('current nonstaff me removes navigation and prevents returning to loaded staff data', async ({ page }) => {
  const state = await mockApi(page, 'staff')
  await page.goto('/users')
  await expect(page.locator('.resource-list')).toContainText('browser-test')
  const calls = state.userCalls.length
  state.profile.is_staff = false
  await navigateTo(page, 'Профиль')
  await expect(page.locator('.details')).toContainText('Нет')
  await openNavigation(page)
  await expect(page.locator('a[href="/users"]')).toHaveCount(0)
  if (await page.getByRole('dialog').isVisible()) await page.keyboard.press('Escape')
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Доступ ограничен' })).toBeVisible()
  await expect(page.locator('.resource-list')).toHaveCount(0)
  expect(state.userCalls.length).toBe(calls)
})

test('late staff response cannot restore data after logout and login as nonstaff', async ({ page }) => {
  const state = await mockApi(page, 'staff')
  await page.goto('/users')
  await expect(page.locator('.resource-list')).toContainText('browser-test')
  state.usersDelay = 1800
  const pending = page.waitForRequest('**/auth/users')
  await page.getByRole('button', { name: 'Обновить список' }).click()
  await pending
  await logout(page)
  state.profile = { user_id: missingId, username: 'another-user', is_staff: false }
  await page.getByRole('link', { name: 'Вход', exact: true }).click()
  await login(page)
  await expect(page.getByRole('heading', { name: 'Мои резюме', exact: true })).toBeVisible()
  await page.goBack()
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Доступ ограничен' })).toBeVisible()
  const calls = state.userCalls.length
  await page.waitForTimeout(1900)
  await expect(page.locator('.resource-list, .details')).toHaveCount(0)
  await openNavigation(page)
  await expect(page.locator('a[href="/users"]')).toHaveCount(0)
  await expect(page.getByText('browser-test', { exact: true })).toHaveCount(0)
  if (await page.getByRole('dialog').isVisible()) await page.keyboard.press('Escape')
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Доступ ограничен' })).toBeVisible()
  expect(state.userCalls.length).toBe(calls)
})

test('staff receives user 404 with a usable return link', async ({ page }) => {
  await mockApi(page, 'staff')
  await page.goto(`/users/${missingId}`)
  await expect(page.getByRole('alert')).toContainText('404')
  await page.getByRole('link', { name: 'Назад: Пользователи' }).click()
  await expect(page.locator('.resource-list')).toContainText('browser-test')
})

test('mobile menu closes on Escape, outside click and navigation with keyboard focus', async ({ page, isMobile }) => {
  test.skip(!isMobile)
  await mockApi(page)
  await page.goto('/profile')
  const burger = page.getByRole('button', { name: 'Открыть меню' })
  await burger.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(burger).toBeFocused()
  await burger.click()
  await page.mouse.click(page.viewportSize()!.width - 10, 400)
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await navigateTo(page, 'Мои резюме')
  await expect(page.getByRole('heading', { name: 'Мои резюме', exact: true })).toBeVisible()
  await expect(page.getByRole('dialog')).not.toBeVisible()
})
