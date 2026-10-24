import { useState } from 'react'
import type { FormEvent } from 'react'
import { addResume, DocumentApiError } from '../api/documents'

function AddResumePage() {
  const [file, setFile] = useState<File | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [needsLogin, setNeedsLogin] = useState(false)
  const [success, setSuccess] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    setError('')
    setNeedsLogin(false)
    setSuccess(false)

    if (!file || !/\.(pdf|docx)$/i.test(file.name)) {
      setError('Выберите файл PDF или DOCX.')
      return
    }

    setPending(true)

    try {
      await addResume(file)
      setSuccess(true)
      setFile(null)
      form.reset()
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
        <h1 id="document-title">Добавить резюме</h1>
        <p className="document-description">Загрузите резюме в формате PDF или DOCX.</p>
        <form onSubmit={submit}>
          <label htmlFor="resume-file">Файл резюме</label>
          <input
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            id="resume-file"
            name="file"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null)
              setError('')
              setNeedsLogin(false)
              setSuccess(false)
            }}
            required
            type="file"
          />
          {error && (
            <p className="form-error" role="alert">
              {error} {needsLogin && <a href="/login">Войти</a>}
            </p>
          )}
          {success && <p className="form-success" role="status">Резюме добавлено.</p>}
          <button className="button button-primary submit-button" disabled={pending} type="submit">
            {pending ? 'Загрузка...' : 'Добавить резюме'}
          </button>
        </form>
      </section>
    </main>
  )
}

export default AddResumePage
