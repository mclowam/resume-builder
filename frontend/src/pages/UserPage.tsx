import { useCallback } from 'react'
import { getUser } from '../api/auth'
import { useResource } from '../app/useResource'
import { ErrorNotice, Loading } from '../components/Feedback'
import Page from '../components/Page'
import UserDetails from '../components/UserDetails'

function UserPage({ id }: { id: string }) {
  const load = useCallback((signal: AbortSignal) => getUser(id, signal), [id])
  const resource = useResource(load)
  return <Page title="Пользователь" back={{ href: '/users', label: 'Пользователи' }}>
    <ErrorNotice error={resource.error} retry={resource.reload} />
    {resource.loading && <Loading />}
    {resource.data && <UserDetails user={resource.data} />}
  </Page>
}

export default UserPage
