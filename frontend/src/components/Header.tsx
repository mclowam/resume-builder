import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { AppShell, Avatar, Burger, Button, Divider, Drawer, Group, NavLink, Stack, Text } from '@mantine/core'
import { useDisclosure, useMediaQuery } from '@mantine/hooks'
import { logout } from '../api/auth'
import { navigate, useLocation } from '../app/navigation'
import { clearDrafts } from '../app/drafts'
import { useSession } from '../app/useSession'
import Icon from './Icon'
import Link from './Link'

function Header({ path, children }: { path: string; children: ReactNode }) {
  const session = useSession()
  const location = useLocation()
  const mobile = useMediaQuery('(max-width: 47.99em)')
  const [opened, { open, close }] = useDisclosure(false)
  useEffect(() => { close() }, [location, mobile, close, session.generation, session.status])
  const authenticated = session.status === 'authenticated'
  const links = [
    { href: '/', label: 'Главная', icon: 'home' as const, active: path === '/' },
    { href: '/my-resumes', label: 'Мои резюме', icon: 'resume' as const, active: path === '/my-resumes' || path === '/add-resume' },
    { href: '/my-vacancies', label: 'Мои вакансии', icon: 'vacancy' as const, active: path.startsWith('/my-vacancies') || path === '/add-vacancy' },
    ...(authenticated && session.user?.is_staff === true ? [{ href: '/users', label: 'Пользователи', icon: 'users' as const, active: path.startsWith('/users') }] : []),
    { href: '/profile', label: 'Профиль', icon: 'profile' as const, active: path === '/profile' },
  ]
  const navigation = <Stack h="100%" gap="xl">
    <div className="sidebar-brand"><span className="brand-mark"><Icon name="resume" /></span><Text fw={700}>Resume Builder</Text></div>
    <div>
      <Text className="nav-caption" size="xs" fw={600} mb="sm">РАБОЧЕЕ ПРОСТРАНСТВО</Text>
      <nav aria-label="Основная навигация"><Stack gap={6}>{links.map((link) => <NavLink component={Link} key={link.href} href={link.href} label={link.label} leftSection={<Icon name={link.icon} />} active={link.active} aria-current={link.active ? 'page' : undefined} onClick={close} className="workspace-link" />)}</Stack></nav>
    </div>
    <Stack mt="auto" gap="md">
      <Divider color="#3b444d" />
      <Group wrap="nowrap" gap="sm">
        <Avatar color="teal" radius="md">{session.user?.username.slice(0, 1).toUpperCase()}</Avatar>
        <div className="account-copy"><Text size="sm" fw={600} truncate title={session.user?.username}>{session.user?.username}</Text><Text size="xs" c="#aebbc7">{session.user?.is_staff === true ? 'Сотрудник' : 'Личный аккаунт'}</Text></div>
      </Group>
      <Button variant="default" className="logout-button" onClick={() => { close(); clearDrafts(); logout(); navigate('/') }}>Выйти</Button>
    </Stack>
  </Stack>

  return <AppShell header={{ height: authenticated ? { base: 64, sm: 0 } : 76 }} navbar={{ width: 240, breakpoint: 'sm', collapsed: { mobile: true, desktop: !authenticated } }} padding={0}>
    <a href="#main" className="skip-link">К содержимому</a>
    <AppShell.Header hiddenFrom={authenticated ? 'sm' : undefined} className="site-header">
      {authenticated ? <Group h="100%" justify="space-between" px="md"><Text fw={700}>Resume Builder</Text><Burger opened={opened} onClick={open} aria-label="Открыть меню" aria-expanded={opened} aria-controls="mobile-menu" size="sm" /></Group> : <Group className="guest-header" h="100%" justify="flex-end">
        {session.status === 'checking' ? <><Text size="sm" role="status">Проверка сессии…</Text><Button variant="default" onClick={logout}>Отменить</Button></> : <nav aria-label="Аккаунт"><Group gap="xs">
          {path !== '/' && <Button component={Link} variant="subtle" href="/">Главная</Button>}
          <Button component={Link} variant="subtle" aria-current={path === '/login' ? 'page' : undefined} href="/login">Вход</Button>
          <Button component={Link} aria-current={path === '/register' ? 'page' : undefined} href="/register">Регистрация</Button>
        </Group></nav>}
      </Group>}
    </AppShell.Header>
    {authenticated && !mobile && <AppShell.Navbar p="lg" className="sidebar">{navigation}</AppShell.Navbar>}
    {authenticated && mobile && <Drawer opened={opened} onClose={close} title="Навигация" size={300} classNames={{ content: 'mobile-navigation', header: 'mobile-navigation', body: 'mobile-navigation-body' }} closeButtonProps={{ 'aria-label': 'Закрыть меню' }} onExitTransitionEnd={close}><div id="mobile-menu">{navigation}</div></Drawer>}
    <AppShell.Main component="div">{children}</AppShell.Main>
  </AppShell>
}

export default Header
