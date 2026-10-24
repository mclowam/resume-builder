import { getUsers } from '../api/auth'
import { useResource } from '../app/useResource'
import { EmptyState, ErrorNotice, Loading } from '../components/Feedback'
import Link from '../components/Link'
import Page from '../components/Page'

function UsersPage() {
  const resource = useResource(getUsers)
  return <Page title="Пользователи" description="Просмотр аккаунтов.">
    <div className="toolbar"><button className="button button-outline" onClick={resource.reload} disabled={resource.loading}>Обновить список</button></div>
    <ErrorNotice error={resource.error} retry={resource.reload} />
    {resource.loading && <Loading />}
    {resource.data?.length === 0 && !resource.loading && !resource.error && <EmptyState title="Пользователи не найдены" description="Список пока пуст." />}
    {!!resource.data?.length && <ul className="resource-list" aria-label="Пользователи" aria-busy={resource.loading}>{resource.data.map((user) => <li className="resource-row" key={user.user_id}><div className="resource-copy"><h2><Link href={`/users/${user.user_id}`}>{user.username}</Link></h2><p className="metadata">{user.is_active ? 'Активен' : 'Неактивен'}{user.is_staff ? ' · Сотрудник' : ''}</p></div><Link className="button button-outline" href={`/users/${user.user_id}`}>Открыть</Link></li>)}</ul>}
  </Page>
}

export default UsersPage
