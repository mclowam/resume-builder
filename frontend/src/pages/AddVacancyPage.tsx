import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { addVacancy } from '../api/documents'
import { navigate } from '../app/navigation'
import { getDraft } from '../app/drafts'
import { ErrorNotice } from '../components/Feedback'
import Page from '../components/Page'

function AddVacancyPage({ userId }: { userId: string }) {
  const [text, setText] = useState(() => getDraft(userId).vacancy)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const busy = useRef(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy.current) return
    setError(null)
    if (!text.trim()) {
      setError(new Error('Введите полный текст вакансии.'))
      return
    }
    busy.current = true
    setPending(true)
    try {
      const vacancy = await addVacancy(text)
      getDraft(userId).vacancy = ''
      navigate(`/my-vacancies/${vacancy.id}?created=1`, true)
    } catch (cause) {
      setError(cause)
    } finally {
      busy.current = false
      setPending(false)
    }
  }

  return <Page title="Добавить вакансию" description="Сохраните описание вакансии одним текстом." back={{ href: '/my-vacancies', label: 'Мои вакансии' }}>
    <form onSubmit={submit} aria-busy={pending}>
      <label htmlFor="vacancy-text">Полный текст вакансии</label>
      <textarea id="vacancy-text" name="text" required rows={12} value={text} disabled={pending} onChange={(event) => { setText(event.target.value); getDraft(userId).vacancy = event.target.value }} aria-describedby="vacancy-help" />
      <p className="field-help" id="vacancy-help">Вставьте описание, требования и условия целиком.</p>
      <ErrorNotice error={error} listPath="/my-vacancies" />
      <button className="button button-primary" disabled={pending} type="submit">{pending ? 'Сохранение…' : 'Сохранить вакансию'}</button>
    </form>
  </Page>
}

export default AddVacancyPage
