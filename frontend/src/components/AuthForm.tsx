import { useState } from 'react'
import type { FormEvent } from 'react'
import { login, register } from '../api/auth'

type AuthFormProps = {
  mode: 'login' | 'register'
}

function AuthForm({ mode }: AuthFormProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [registered, setRegistered] = useState(false)
  const isLogin = mode === 'login'

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setPending(true)

    try {
      const credentials = { username: username.trim(), password }

      if (isLogin) {
        const tokens = await login(credentials)
        sessionStorage.setItem('access_token', tokens.access_token)
        sessionStorage.setItem('refresh_token', tokens.refresh_token)
        sessionStorage.setItem('username', credentials.username)
        window.location.assign('/')
      } else {
        await register(credentials)
        setRegistered(true)
        setPassword('')
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Неизвестная ошибка. Попробуйте позже.')
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-card" aria-labelledby="auth-title">
        <h1 id="auth-title">{isLogin ? 'Вход' : 'Регистрация'}</h1>
        {registered ? (
          <div className="auth-success" role="status">
            <p>Аккаунт создан. Теперь можно войти.</p>
            <a className="button button-primary" href="/login">Перейти ко входу</a>
          </div>
        ) : (
          <>
            <p className="auth-description">
              {isLogin ? 'Войдите в свой аккаунт.' : 'Создайте аккаунт, чтобы начать работу.'}
            </p>
            <form onSubmit={submit}>
              <label htmlFor="username">Имя пользователя</label>
              <input
                autoComplete="username"
                id="username"
                name="username"
                onChange={(event) => setUsername(event.target.value)}
                required
                type="text"
                value={username}
              />
              <label htmlFor="password">Пароль</label>
              <input
                autoComplete={isLogin ? 'current-password' : 'new-password'}
                id="password"
                name="password"
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
              {error && <p className="form-error" role="alert">{error}</p>}
              <button className="button button-primary submit-button" disabled={pending} type="submit">
                {pending ? 'Подождите...' : isLogin ? 'Войти' : 'Зарегистрироваться'}
              </button>
            </form>
            <p className="auth-switch">
              {isLogin ? 'Нет аккаунта?' : 'Уже есть аккаунт?'}{' '}
              <a href={isLogin ? '/register' : '/login'}>{isLogin ? 'Зарегистрироваться' : 'Войти'}</a>
            </p>
          </>
        )}
      </section>
    </main>
  )
}

export default AuthForm
