import { ApiError } from '../api/client'
import ForbiddenPage from './ForbiddenPage'
import { Button } from '@mantine/core'
import { useCallback } from 'react'
import { getUser } from '../api/auth'
import { useResource } from '../app/useResource'
import { ErrorNotice, Loading } from '../components/Feedback'
import Page from '../components/Page'
import UserDetails from '../components/UserDetails'

function UserPage({ id }: { id: string }) {
  const load = useCallback((signal: AbortSignal) => getUser(id, signal), [id])
  const resource = useResource(load, true)
  if (resource.error instanceof ApiError && resource.error.status === 403) return <ForbiddenPage />
  return <Page title="Пользователь" back={{ href: '/users', label: 'Пользователи' }}>
    <div className="toolbar"><Button variant="default" onClick={resource.reload} disabled={resource.loading}>Обновить профиль</Button></div>
    <ErrorNotice error={resource.error} retry={resource.reload} />
    {resource.loading && <Loading />}
    {resource.data && <UserDetails user={resource.data} />}
  </Page>
}

export default UserPage
