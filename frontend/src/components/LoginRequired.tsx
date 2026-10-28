import { Alert, Button, Group } from '@mantine/core'
import { authPath } from '../app/routes'
import { useSession } from '../app/useSession'
import Link from './Link'
import Page from './Page'

function LoginRequired({ path }: { path: string }) {
  const session = useSession()
  return <Page title="Войдите в аккаунт" description="Ваши документы доступны после входа." narrow>
    {session.message && <Alert role="status" mb="lg">{session.message}</Alert>}
    <Group><Button component={Link} href={authPath('login', path)}>Войти</Button><Button component={Link} variant="default" href={authPath('register', path)}>Создать аккаунт</Button></Group>
  </Page>
}

export default LoginRequired
