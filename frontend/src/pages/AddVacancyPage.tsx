import { useState } from 'react'
import type { FormEvent } from 'react'
import { addVacancy, DocumentApiError } from '../api/documents'

function AddVacancyPage() {
  const [text, setText] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [needsLogin, setNeedsLogin] = useState(false)
  const [success, setSuccess] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setNeedsLogin(false)
    setSuccess(false)

    const vacancyText = text.trim()

    if (!vacancyText) {
      setError('Введите текст вакансии.')
      return
    }

    setPending(true)

    try {
      await addVacancy(vacancyText)
      setSuccess(true)
      setText('')
    } catch (cause) {
      setNeedsLogin(cause instanceof DocumentApiError && cause.status === 401)
      setError(cause instanceof Error ? cause.message : 'Неизвестная ошибка. Попробуйте позже.')
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="document-layout">
      <section className="document-card" aria-labelledby="document-title">
        <h1 id="document-title">Добавить вакансию</h1>
        <p className="document-description">Вставьте полный текст вакансии.</p>
        <form onSubmit={submit}>
          <label htmlFor="vacancy-text">Текст вакансии</label>
          <textarea
            id="vacancy-text"
            name="text"
            onChange={(event) => {
              setText(event.target.value)
              setError('')
              setNeedsLogin(false)
              setSuccess(false)
            }}
            required
            rows={10}
            value={text}
          />
          {error && (
            <p className="form-error" role="alert">
              {error} {needsLogin && <a href="/login">Войти</a>}
            </p>
          )}
          {success && <p className="form-success" role="status">Вакансия добавлена.</p>}
          <button className="button button-primary submit-button" disabled={pending} type="submit">
            {pending ? 'Сохранение...' : 'Добавить вакансию'}
          </button>
        </form>
      </section>
    </main>
  )
}

export default AddVacancyPage
