import { useRef, useState } from 'react'
import { Button, Input, Text, ThemeIcon } from '@mantine/core'
import Icon from '../components/Icon'
import type { FormEvent } from 'react'
import { addResume } from '../api/documents'
import { navigate } from '../app/navigation'
import { getDraft } from '../app/drafts'
import { ErrorNotice } from '../components/Feedback'
import Page from '../components/Page'

function AddResumePage({ userId }: { userId: string }) {
  const [file, setFile] = useState<File | null>(() => getDraft(userId).resume)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const busy = useRef(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy.current) return
    setError(null)
    if (!file || !/\.(pdf|docx)$/i.test(file.name) || file.size === 0) {
      setError(new Error('Выберите непустой файл PDF или DOCX.'))
      return
    }
    busy.current = true
    setPending(true)
    try {
      await addResume(file)
      getDraft(userId).resume = null
      navigate('/my-resumes?created=1', true)
    } catch (cause) {
      setError(cause)
    } finally {
      busy.current = false
      setPending(false)
    }
  }

  return <Page title="Добавить резюме" description="Загрузите готовый документ целиком." back={{ href: '/my-resumes', label: 'Мои резюме' }} narrow>
    <form onSubmit={submit} aria-busy={pending} className="form-stack">
      <div className="file-field">
        <ThemeIcon size={44} variant="light" mb="md"><Icon name="upload" size={24} /></ThemeIcon>
        <Input.Wrapper id="resume-file" label="Файл резюме" description="PDF или DOCX, без пароля. После загрузки документ появится в списке." required>
          <input className="file-input" id="resume-file" name="file" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" required={!file} disabled={pending} aria-describedby="resume-file-description" onChange={(event) => { const selected = event.target.files?.[0] || null; setFile(selected); getDraft(userId).resume = selected; setError(null) }} />
        </Input.Wrapper>
      </div>
      {file && <Text className="selected-file" size="sm">Выбран: {file.name}</Text>}
      <ErrorNotice error={error} listPath="/my-resumes" />
      <Button type="submit" loading={pending} disabled={pending}>{pending ? 'Загрузка…' : 'Загрузить резюме'}</Button>
    </form>
  </Page>
}

export default AddResumePage
