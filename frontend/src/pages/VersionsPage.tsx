import { Button } from '@mantine/core'
import { useSyncExternalStore } from 'react'
import { getDraft, subscribeDrafts } from '../app/drafts'
import Link from '../components/Link'
import Page from '../components/Page'

function VersionsPage({ userId }: { userId: string }) {
  const versions = useSyncExternalStore(subscribeDrafts, () => getDraft(userId).versions)
  const labels = { pending: 'В очереди', running: 'Обрабатывается', done: 'Готово', failed: 'Ошибка обработки' }
  return <Page title="Мои версии" description="Версии, открытые или созданные в этой вкладке. После перезагрузки список очищается; сохранённый результат можно открыть по его ссылке.">
    {versions.length ? <div className="version-list">{versions.map((item) => <Link key={item.id} className="version-row" href={`/my-versions/${item.id}`}><div><strong>{item.title || 'Версия резюме'}</strong><p>{new Date(item.created_at).toLocaleString('ru-RU')}</p></div><span>{labels[item.status]}</span></Link>)}</div> : <div className="empty-state"><h2>Здесь начнётся ваша история</h2><p>Добавьте вакансию — мы подготовим отдельную версию исходного резюме.</p></div>}
    <Button component={Link} href="/workspace" mt="xl">Создать версию</Button>
  </Page>
}

export default VersionsPage
