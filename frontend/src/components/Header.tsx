import { logout } from '../api/auth'
import { navigate } from '../app/navigation'
import { clearDrafts } from '../app/drafts'
import { useSession } from '../app/useSession'
import Link from './Link'

function Header({ path }: { path: string }) {
  const session = useSession()
  const links = [
    { href: '/', label: 'Главная', active: path === '/' },
    { href: '/my-resumes', label: 'Мои резюме', active: path === '/my-resumes' || path === '/add-resume' },
    { href: '/my-vacancies', label: 'Мои вакансии', active: path.startsWith('/my-vacancies') || path === '/add-vacancy' },
    { href: '/users', label: 'Пользователи', active: path.startsWith('/users') },
    { href: '/profile', label: 'Профиль', active: path === '/profile' },
  ]

  return <header className="site-header">
    <a href="#main" className="skip-link">К содержимому</a>
    <div className="header-inner">
      {session.user ? <>
        <nav className="main-nav" aria-label="Основная навигация">{links.map((link) => <Link key={link.href} href={link.href} aria-current={link.active ? 'page' : undefined}>{link.label}</Link>)}</nav>
        <div className="header-actions"><span className="header-username" title={session.user.username}>{session.user.username}</span><button className="button button-outline" onClick={() => { clearDrafts(); logout(); navigate('/') }}>Выйти</button></div>
      </> : session.status === 'checking' ? <div className="header-actions"><span role="status">Проверка сессии…</span><button className="button button-outline" onClick={logout}>Отменить</button></div> : <nav className="header-actions" aria-label="Аккаунт">
        {path !== '/' && <Link className="button button-text" href="/">Главная</Link>}
        <Link className="button button-text" aria-current={path === '/login' ? 'page' : undefined} href="/login">Вход</Link>
        <Link className="button button-primary" aria-current={path === '/register' ? 'page' : undefined} href="/register">Регистрация</Link>
      </nav>}
    </div>
  </header>
}

export default Header
