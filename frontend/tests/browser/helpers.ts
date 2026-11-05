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
  if (await burger.isVisible()) {
    if (!await page.getByRole('dialog').isVisible()) await burger.click()
    await expect(page.getByRole('dialog')).toBeVisible()
  } else if (!await page.getByRole('menu').isVisible()) {
    await page.getByRole('button', { name: /^Аккаунт / }).click()
    await expect(page.getByRole('menu')).toBeVisible()
  }
}

export function navigationLink(page: Page, name: string) {
  return page.locator('a[role="menuitem"], .mobile-navigation a, .desktop-navigation a').filter({ hasText: new RegExp(`^${name}$`) }).filter({ visible: true })
}

export async function navigateTo(page: Page, name: string) {
  await openNavigation(page)
  await navigationLink(page, name).click()
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(page.getByRole('menu')).not.toBeVisible()
}

export async function logout(page: Page) {
  await openNavigation(page)
  const burger = page.getByRole('button', { name: 'Открыть меню' })
  if (await burger.isVisible()) await page.getByRole('button', { name: 'Выйти' }).click()
  else await page.getByRole('menuitem', { name: 'Выйти' }).click()
}
