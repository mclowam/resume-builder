function Header() {
  const isLoggedIn = Boolean(sessionStorage.getItem('access_token'))

  function logout() {
    sessionStorage.removeItem('access_token')
    sessionStorage.removeItem('refresh_token')
    sessionStorage.removeItem('username')
    window.location.assign('/')
  }

  return (
    <header className="site-header">
      <div className="header-inner">
        <nav aria-label="Основная навигация" className="header-actions">
          {isLoggedIn ? (
            <>
              <a className="button button-text" href="/add-resume">Добавить резюме</a>
              <a className="button button-text" href="/add-vacancy">Добавить вакансию</a>
              <span className="header-username">{sessionStorage.getItem('username')}</span>
              <button className="button button-outline" onClick={logout} type="button">Выйти</button>
            </>
          ) : (
            <>
              <a className="button button-text" href="/login">Вход</a>
              <a className="button button-primary" href="/register">Регистрация</a>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}

export default Header
