import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { Burger, Button, Drawer, Menu, Stack, Text } from '@mantine/core'
import { useDisclosure, useMediaQuery } from '@mantine/hooks'
import { logout } from '../api/auth'
import { navigate, useLocation } from '../app/navigation'
import { clearDrafts } from '../app/drafts'
import { useSession } from '../app/useSession'
import Link from './Link'

function Header({ path, children }: { path: string; children: ReactNode }) {
  const session = useSession()
  const location = useLocation()
  const mobile = useMediaQuery('(max-width: 47.99em)')
  const [opened, { open, close }] = useDisclosure(false)
  useEffect(() => { close() }, [location, mobile, close, session.generation, session.status])
  const authenticated = session.status === 'authenticated'
  const links = [
    { href: '/workspace', label: 'Рабочее пространство', active: path === '/workspace' || path === '/add-vacancy' },
    { href: '/my-versions', label: 'Мои версии', active: path === '/my-versions' || path.startsWith('/my-versions/') },
  ]
  const accountLinks = [
    { href: '/my-resumes', label: 'Мои резюме' },
    { href: '/my-vacancies', label: 'Мои вакансии' },
    { href: '/profile', label: 'Профиль' },
    ...(authenticated && session.user?.is_staff === true ? [{ href: '/users', label: 'Пользователи' }] : []),
  ]

  function signOut() {
    close()
    clearDrafts()
    logout()
    navigate('/')
  }

  return <div className="site-shell">
    <a href="#main" className="skip-link">К содержимому</a>
    <header className="site-header">
      <div className="header-inner">
        <Link href={authenticated ? '/workspace' : '/'} className="wordmark" aria-label="Resume Builder">resume <span>/</span> builder</Link>
        {authenticated ? <>
          <nav className="desktop-navigation" aria-label="Основная навигация">{links.map((link) => <Link key={link.href} href={link.href} aria-current={link.active ? 'page' : undefined}>{link.label}</Link>)}</nav>
          <div className="desktop-account">
            <Menu position="bottom-end" width={220} shadow="sm" offset={12}>
              <Menu.Target><button type="button" className="account-button" aria-label={`Аккаунт ${session.user?.username}`}>{session.user?.username.slice(0, 2).toUpperCase()}</button></Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>{session.user?.username}</Menu.Label>
                {accountLinks.map((link) => <Menu.Item component={Link} href={link.href} key={link.href}>{link.label}</Menu.Item>)}
                <Menu.Divider />
                <Menu.Item onClick={signOut}>Выйти</Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </div>
          <Burger className="mobile-burger" opened={opened} onClick={open} aria-label="Открыть меню" aria-expanded={opened} aria-controls="mobile-menu" size="sm" />
        </> : <nav className="guest-navigation" aria-label="Аккаунт">
          {session.status === 'checking' ? <><Text size="sm" role="status">Проверка сессии…</Text><Button variant="default" onClick={logout}>Отменить</Button></> : <>
            <Link aria-current={path === '/login' ? 'page' : undefined} href="/login">Вход</Link>
            <Button component={Link} aria-current={path === '/register' ? 'page' : undefined} href="/register">Регистрация</Button>
          </>}
        </nav>}
      </div>
    </header>
    {authenticated && mobile && <Drawer opened={opened} onClose={close} title="Навигация" position="right" size={320} closeButtonProps={{ 'aria-label': 'Закрыть меню' }} classNames={{ content: 'mobile-navigation', body: 'mobile-navigation-body' }}>
      <nav id="mobile-menu" aria-label="Основная навигация"><Stack gap={4}>{[...links, ...accountLinks].map((link) => <Link className="mobile-nav-link" href={link.href} key={link.href} aria-current={path === link.href ? 'page' : undefined} onClick={close}>{link.label}</Link>)}</Stack></nav>
      <div className="mobile-account"><Text size="sm" c="dimmed">{session.user?.username}</Text><Button variant="default" onClick={signOut}>Выйти</Button></div>
    </Drawer>}
    {children}
  </div>
}

export default Header
