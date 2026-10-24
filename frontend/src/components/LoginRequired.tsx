function LoginRequired() {
  return (
    <main className="document-layout">
      <section className="document-card">
        <h1>Войдите в аккаунт</h1>
        <p className="document-description">Чтобы добавить резюме или вакансию, сначала войдите.</p>
        <a className="button button-primary" href="/login">Войти</a>
      </section>
    </main>
  )
}

export default LoginRequired
