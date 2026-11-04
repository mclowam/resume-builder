import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Textarea } from '@mantine/core'
import { getAdaptation } from '../api/documents'
import { rememberVersion } from '../app/drafts'
import { ErrorNotice, Loading } from '../components/Feedback'
import Link from '../components/Link'
import Page from '../components/Page'
import type { Adaptation } from '../types/api'

function AdaptationPage({ id, userId }: { id: string; userId: string }) {
  const [version, setVersion] = useState<Adaptation | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [revision, setRevision] = useState(0)
  const [copied, setCopied] = useState('')
  const text = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    setVersion(null)
    setError(null)
    async function poll() {
      try {
        const result = await getAdaptation(id, controller.signal)
        if (controller.signal.aborted) return
        setVersion(result)
        rememberVersion(userId, result)
        if (result.status === 'pending' || result.status === 'running') timer = setTimeout(() => { void poll() }, 2000)
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause)
      }
    }
    void poll()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [id, userId, revision])

  async function copy() {
    if (!version?.result) return
    try {
      if (!navigator.clipboard) throw new Error('Clipboard unavailable')
      await navigator.clipboard.writeText(version.result.resume_text)
      setCopied('Текст скопирован.')
    } catch {
      text.current?.focus()
      text.current?.select()
      setCopied('Текст выделен. Скопируйте его сочетанием Ctrl+C или через меню устройства.')
    }
  }

  return <Page title="Версия резюме" description="Отдельная адаптация под выбранную вакансию." back={{ href: '/my-versions', label: 'Мои версии' }}>
    <ErrorNotice error={error} retry={() => setRevision((value) => value + 1)} />
    {!version && !error && <Loading text="Получаем результат…" />}
    {version && <>
      {(version.status === 'pending' || version.status === 'running') && <div role="status" className="processing-state"><Loading text={version.status === 'pending' ? 'Задача в очереди' : 'Адаптируем резюме и проверяем факты…'} /><p>Результат появится здесь автоматически. Оригинал сохранён отдельно.</p></div>}
      {version.status === 'failed' && <Alert color="red" title="Не удалось подготовить версию" role="alert">Во время обработки произошла техническая ошибка. Исходное резюме сохранено. Вы можете <Link href={`/workspace?vacancy=${version.vacancy_id}`}>создать новую попытку</Link>.</Alert>}
      {version.status === 'done' && version.result && <div className="result-layout">
        <section className="result-document"><Textarea ref={text} label="Адаптированный текст резюме" readOnly autosize minRows={18} value={version.result.resume_text} /><div className="result-actions"><Button onClick={() => { void copy() }}>Скопировать текст</Button><span role="status">{copied}</span></div></section>
        <aside className="result-review"><h2>Проверка фактов</h2>{version.result.review.passed ? <p>Проверка не выявила неподтверждённых фактов.</p> : <><p>Проверьте замечания перед отправкой работодателю.</p><ul>{version.result.review.issues.map((issue, index) => <li key={index}>{issue}</li>)}</ul></>}<p>Проверку выполняет AI. Перечитайте результат перед использованием.</p><Link href={`/my-vacancies/${version.vacancy_id}`}>Открыть вакансию</Link></aside>
      </div>}
    </>}
  </Page>
}

export default AdaptationPage
