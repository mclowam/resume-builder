import { ApiError } from '../api/client'
import ForbiddenPage from './ForbiddenPage'
import { Button, Paper } from '@mantine/core'
import { getUsers } from '../api/auth'
import { useResource } from '../app/useResource'
import { EmptyState, ErrorNotice, Loading } from '../components/Feedback'
import Link from '../components/Link'
import Page from '../components/Page'

function UsersPage() {
  const resource = useResource(getUsers, true)
  if (resource.error instanceof ApiError && resource.error.status === 403) return <ForbiddenPage />
  return <Page title="Пользователи" description="Просмотр аккаунтов.">
    <div className="toolbar"><Button variant="default" onClick={resource.reload} disabled={resource.loading}>Обновить список</Button></div>
    <ErrorNotice error={resource.error} retry={resource.reload} />
    {resource.loading && <Loading />}
    {resource.data?.length === 0 && !resource.loading && !resource.error && <EmptyState title="Пользователи не найдены" description="Список пока пуст." />}
    {!!resource.data?.length && <ul className="resource-list" aria-label="Пользователи" aria-busy={resource.loading}>{resource.data.map((user) => <Paper component="li" className="resource-row" key={user.user_id}><div className="resource-copy"><h2><Link href={`/users/${user.user_id}`}>{user.username}</Link></h2><p className="metadata">{user.is_active ? 'Активен' : 'Неактивен'}{user.is_staff ? ' · Сотрудник' : ''}</p></div><Button component={Link} variant="default" href={`/users/${user.user_id}`}>Открыть</Button></Paper>)}</ul>}
  </Page>
}

export default UsersPage
