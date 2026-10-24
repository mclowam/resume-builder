import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { login, register } from '../api/auth'
import { navigate } from '../app/navigation'
import { authPath, safeReturnPath } from '../app/routes'
import { useSession } from '../app/useSession'
import { ErrorNotice } from './Feedback'
import Link from './Link'
import Page from './Page'

function AuthForm({ mode }: { mode: 'login' | 'register' }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [registered, setRegistered] = useState(false)
  const busy = useRef(false)
  const session = useSession()
  const isLogin = mode === 'login'
  const next = safeReturnPath(new URLSearchParams(window.location.search).get('next'))

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy.current) return
    setError(null)
    if (!username.trim() || !password.trim()) {
      setError(new Error('Введите имя пользователя и пароль.'))
      return
    }
    busy.current = true
    setPending(true)
    try {
      const credentials = { username: username.trim(), password }
      if (isLogin) {
        await login(credentials)
        navigate(next, true)
      } else {
        await register(credentials)
        setRegistered(true)
        setPassword('')
      }
    } catch (cause) {
      setError(cause)
    } finally {
      busy.current = false
      setPending(false)
    }
  }

  return <Page title={isLogin ? 'Вход' : 'Регистрация'} description={isLogin ? 'Войдите, чтобы работать со своими документами.' : 'Создайте аккаунт для резюме и вакансий.'} narrow>
    {session.user ? <div className="empty-state"><p>Вы вошли как {session.user.username}.</p><Link className="button button-primary" href={next}>Продолжить</Link></div> : registered ? <div className="notice notice-success" role="status"><p>Аккаунт создан. Теперь можно войти.</p><Link className="button button-primary" href={authPath('login', next)}>Перейти ко входу</Link></div> : <>
      {session.message && <p className="notice" role="status">{session.message}</p>}
      <form onSubmit={submit} aria-busy={pending}>
        <label htmlFor="username">Имя пользователя</label>
        <input autoComplete="username" autoCapitalize="none" spellCheck={false} id="username" name="username" required value={username} onChange={(event) => setUsername(event.target.value)} disabled={pending} />
        <label htmlFor="password">Пароль</label>
        <input autoComplete={isLogin ? 'current-password' : 'new-password'} id="password" name="password" required type="password" value={password} onChange={(event) => setPassword(event.target.value)} disabled={pending} />
        <ErrorNotice error={error} />
        <button className="button button-primary" disabled={pending} type="submit">{pending ? 'Подождите…' : isLogin ? 'Войти' : 'Зарегистрироваться'}</button>
      </form>
      <p className="auth-switch">{isLogin ? 'Нет аккаунта?' : 'Уже есть аккаунт?'} <Link href={authPath(isLogin ? 'register' : 'login', next)}>{isLogin ? 'Зарегистрироваться' : 'Войти'}</Link></p>
    </>}
  </Page>
}

export default AuthForm
