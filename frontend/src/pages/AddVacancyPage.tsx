import { useRef, useState } from 'react'
import { Button, Textarea } from '@mantine/core'
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

  return <Page title="Добавить вакансию" description="Сохраните описание вакансии полным текстом." back={{ href: '/my-vacancies', label: 'Мои вакансии' }}>
    <form onSubmit={submit} aria-busy={pending} className="form-stack document-form">
      <Textarea label="Полный текст вакансии" description="Вставьте описание, требования и условия целиком." id="vacancy-text" name="text" required minRows={12} autosize value={text} disabled={pending} onChange={(event) => { setText(event.target.value); getDraft(userId).vacancy = event.target.value }} />
      <ErrorNotice error={error} listPath="/my-vacancies" />
      <Button loading={pending} disabled={pending} type="submit">{pending ? 'Сохранение…' : 'Сохранить вакансию'}</Button>
    </form>
  </Page>
}

export default AddVacancyPage
