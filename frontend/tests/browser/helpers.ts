import { expect } from '@playwright/test'
import type { Page } from '@playwright/test'

export async function login(page: Page) {
  await page.getByLabel('Имя пользователя').fill('browser-test')
  await page.getByLabel('Пароль', { exact: true }).fill('browser-password')
  await page.getByRole('button', { name: 'Войти', exact: true }).click()
}

export async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
}

export async function openNavigation(page: Page) {
  const burger = page.getByRole('button', { name: 'Открыть меню' })
  if (await burger.isVisible() && !await page.getByRole('navigation', { name: 'Основная навигация' }).isVisible()) await burger.click()
  if (await burger.isVisible()) await expect.poll(async () => Math.round((await page.getByRole('dialog').boundingBox())?.x ?? -1)).toBe(0)
}

export async function navigateTo(page: Page, name: string) {
  await openNavigation(page)
  await page.getByRole('navigation', { name: 'Основная навигация' }).getByRole('link', { name, exact: true }).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
}

export async function logout(page: Page) {
  await openNavigation(page)
  await page.getByRole('button', { name: 'Выйти' }).click()
}
