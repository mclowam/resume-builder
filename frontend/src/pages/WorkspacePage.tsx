import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Anchor, Button, Select, Textarea } from '@mantine/core'
import { ApiError } from '../api/client'
import { addAdaptation, addVacancy, downloadResume, getResumes, getVacancy, resumeName } from '../api/documents'
import { getSession } from '../api/session'
import { getDraft, rememberVersion } from '../app/drafts'
import { navigate } from '../app/navigation'
import { ErrorNotice, Loading } from '../components/Feedback'
import Link from '../components/Link'
import type { Resume, Vacancy } from '../types/api'

function WorkspacePage({ userId }: { userId: string }) {
  const [resumes, setResumes] = useState<Resume[]>([])
  const [sourceId, setSourceId] = useState(() => getDraft(userId).sourceId)
  const [text, setText] = useState(() => getDraft(userId).vacancy)
  const [savedVacancy, setSavedVacancy] = useState<Vacancy | null>(() => {
    const draft = getDraft(userId)
    return draft.savedVacancy?.text === draft.vacancy ? draft.savedVacancy : null
  })
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState(false)
  const [uncertain, setUncertain] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [revision, setRevision] = useState(0)
  const busy = useRef(false)
  const mounted = useRef(true)
  const heading = useRef<HTMLHeadingElement>(null)
  const vacancyId = new URLSearchParams(window.location.search).get('vacancy')

  useEffect(() => {
    mounted.current = true
    document.title = 'Рабочее пространство — Resume Builder'
    heading.current?.focus()
    return () => { mounted.current = false }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    const validVacancy = vacancyId && /^[a-f0-9-]{36}$/i.test(vacancyId)
    Promise.all([getResumes(controller.signal), validVacancy ? getVacancy(vacancyId, controller.signal) : Promise.resolve(null)]).then(([items, vacancy]) => {
      if (controller.signal.aborted) return
      setResumes(items)
      const selected = items.some((item) => item.id === getDraft(userId).sourceId) ? getDraft(userId).sourceId : items[0]?.id || ''
      setSourceId(selected)
      getDraft(userId).sourceId = selected
      if (vacancy) {
        setSavedVacancy(vacancy)
        setText(vacancy.text)
        getDraft(userId).vacancy = vacancy.text
        getDraft(userId).savedVacancy = vacancy
      }
      setError(null)
    }).catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause) }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [userId, vacancyId, revision])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy.current || uncertain || !sourceId || !text.trim()) return
    busy.current = true
    setPending(true)
    setError(null)
    const generation = getSession().generation
    try {
      const vacancy = savedVacancy || await addVacancy(text)
      if (generation !== getSession().generation) return
      getDraft(userId).savedVacancy = vacancy
      if (mounted.current) setSavedVacancy(vacancy)
      const version = await addAdaptation(sourceId, vacancy.id)
      if (generation !== getSession().generation) return
      rememberVersion(userId, version, text.split('\n').find((line) => line.trim())?.trim().slice(0, 80))
      if (getDraft(userId).vacancy === text) {
        getDraft(userId).vacancy = ''
        getDraft(userId).savedVacancy = null
      }
      if (mounted.current) navigate(`/my-versions/${version.id}`)
    } catch (cause) {
      if (mounted.current && generation === getSession().generation) {
        setError(cause)
        setUncertain(cause instanceof ApiError && cause.uncertain)
      }
    } finally {
      busy.current = false
      if (mounted.current) setPending(false)
    }
  }

  const source = resumes.find((item) => item.id === sourceId)
  const versions = getDraft(userId).versions.slice(0, 3)
  return <main id="main" className="page workspace">
    <header className="workspace-hero">
      <div className="hero-copy"><h1 ref={heading} tabIndex={-1}><span className="hero-strong">Ваш опыт.</span><span className="hero-light">Для <span className="hero-accent">новой роли.</span></span></h1><p>Адаптируйте резюме под конкретную вакансию.</p></div>
      <nav className="workflow-steps" aria-label="Этапы адаптации"><span>01 Резюме</span><span className="is-current" aria-current="step">02 Вакансия</span><span>03 Результат</span></nav>
    </header>
    {loading && <Loading text="Загружаем ваши документы…" />}
    <div className="workspace-grid">
      <aside className="workspace-source">
        <h2>Исходное резюме</h2>
        {source ? <>
          <div className="source-document"><span className="source-format">{resumeName(source).split('.').pop()?.toUpperCase() || 'ДОКУМЕНТ'}</span><h3>{resumeName(source)}</h3><p>Ваш исходный документ</p><p>Для каждой вакансии создаётся отдельная версия.</p><Button variant="subtle" onClick={() => { void downloadResume(source.id, resumeName(source)).catch(setError) }}>Скачать оригинал</Button></div>
          <p className="source-status">Оригинал сохранён</p>
          {resumes.length > 1 && <Select label="Исходное резюме" value={sourceId} disabled={pending} data={resumes.map((item) => ({ value: item.id, label: resumeName(item) }))} onChange={(value) => { setSourceId(value || ''); getDraft(userId).sourceId = value || '' }} />}
          <Anchor component={Link} href="/add-resume?next=workspace">Загрузить другое</Anchor>
        </> : !loading && <div className="source-document"><strong>Начните с вашего опыта</strong><p>Загрузите резюме один раз, чтобы создавать версии под разные вакансии.</p><Button component={Link} href="/add-resume?next=workspace">Загрузить резюме</Button></div>}
        <section className="workspace-recent"><h3>Недавние версии</h3><p>В этой вкладке</p>{versions.length ? <div className="version-list">{versions.map((item) => <Link className="version-row" key={item.id} href={`/my-versions/${item.id}`}><strong>{item.title || 'Версия резюме'}</strong><p>{new Date(item.created_at).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</p></Link>)}</div> : <p>Здесь появятся созданные вами версии.</p>}</section>
      </aside>
      <section className="workspace-editor"><h2>Добавьте вакансию</h2><p>Вставьте описание, задачи и требования.</p>
        <form className="form-stack" aria-busy={pending} onSubmit={submit}>
          <Textarea className="vacancy-input" aria-label="Полный текст вакансии" placeholder="Вставьте сюда текст вакансии…" minRows={12} required maxLength={10000} value={text} disabled={pending || loading || uncertain} onChange={(event) => { const value = event.target.value; setText(value); getDraft(userId).vacancy = value; getDraft(userId).savedVacancy = null; setSavedVacancy(null) }} />
          <div className="workspace-editor-meta"><span>{savedVacancy ? 'Вакансия сохранена' : 'Полный текст вакансии'}</span><span>{text.length.toLocaleString('ru-RU')} / 10 000</span></div>
          <ErrorNotice error={error} retry={!uncertain && !pending && !source ? () => setRevision((value) => value + 1) : undefined} />
          {uncertain && <p role="status">Сервер мог принять задачу, но ответ не получен. Не отправляйте её повторно автоматически. Сохранённые вакансии доступны в разделе <Link href="/my-vacancies">«Мои вакансии»</Link>.</p>}
          <div className="workspace-submit"><Button type="submit" disabled={loading || pending || uncertain || !source || !text.trim()} loading={pending}>{pending ? 'Создаём версию…' : 'Создать версию'}</Button><p>Исходное резюме останется без изменений.</p></div>
        </form>
      </section>
    </div>
  </main>
}

export default WorkspacePage
