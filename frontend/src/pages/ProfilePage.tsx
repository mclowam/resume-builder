import { getProfile } from '../api/auth'
import { useResource } from '../app/useResource'
import { ErrorNotice, Loading } from '../components/Feedback'
import Page from '../components/Page'
import UserDetails from '../components/UserDetails'

function ProfilePage() {
  const resource = useResource(getProfile)
  return <Page title="Профиль" description="Данные текущего аккаунта.">
    <ErrorNotice error={resource.error} retry={resource.reload} />
    {resource.loading && <Loading />}
    {resource.data && <UserDetails user={resource.data} />}
  </Page>
}

export default ProfilePage
