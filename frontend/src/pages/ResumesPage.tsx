import { useEffect, useRef, useState } from 'react'
import { downloadResume, getResumes, resumeName } from '../api/documents'
import { useResource } from '../app/useResource'
import { EmptyState, ErrorNotice, Loading } from '../components/Feedback'
import Link from '../components/Link'
import Page from '../components/Page'
import type { Resume } from '../types/api'

function ResumesPage() {
  const resource = useResource(getResumes)
  const [downloading, setDownloading] = useState<string | null>(null)
  const [downloadError, setDownloadError] = useState<unknown>(null)
  const [downloaded, setDownloaded] = useState('')
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])

  async function download(resume: Resume) {
    if (controller.current) return
    const active = new AbortController()
    controller.current = active
    setDownloading(resume.id)
    setDownloadError(null)
    setDownloaded('')
    try {
      const filename = await downloadResume(resume.id, resumeName(resume), active.signal)
      if (!active.signal.aborted) setDownloaded(filename)
    } catch (cause) {
      if (!active.signal.aborted) setDownloadError(cause)
    } finally {
      controller.current = null
      if (!active.signal.aborted) setDownloading(null)
    }
  }

  return <Page title="Мои резюме" description="Загруженные документы вашего аккаунта.">
    <div className="toolbar"><Link className="button button-primary" href="/add-resume">Добавить резюме</Link><button className="button button-outline" onClick={resource.reload} disabled={resource.loading}>Обновить список</button></div>
    {new URLSearchParams(window.location.search).has('created') && <p className="notice notice-success" role="status">Резюме загружено.</p>}
    <ErrorNotice error={resource.error} retry={resource.reload} />
    <ErrorNotice error={downloadError} />
    {downloaded && <p className="notice notice-success" role="status">Файл «{downloaded}» передан браузеру для скачивания.</p>}
    {resource.loading && <Loading />}
    {resource.data?.length === 0 && !resource.loading && !resource.error && <EmptyState title="Пока нет резюме" description="Добавьте первый PDF или DOCX, чтобы он появился здесь." />}
    {!!resource.data?.length && <ul className="resource-list" aria-label="Резюме" aria-busy={resource.loading}>
      {[...resource.data].sort((a, b) => b.created_at.localeCompare(a.created_at)).map((resume) => <li key={resume.id} className="resource-row"><div className="resource-copy"><h2>{resumeName(resume)}</h2><p className="metadata">Загружено: <time dateTime={resume.created_at}>{Number.isNaN(Date.parse(resume.created_at)) ? 'Дата недоступна' : new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(resume.created_at))}</time></p></div><button className="button button-outline" disabled={downloading !== null} onClick={() => void download(resume)} aria-label={`Скачать ${resumeName(resume)}`}>{downloading === resume.id ? 'Скачивание…' : 'Скачать'}</button></li>)}
    </ul>}
  </Page>
}

export default ResumesPage
