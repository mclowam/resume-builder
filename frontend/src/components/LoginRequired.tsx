import { authPath } from '../app/routes'
import { useSession } from '../app/useSession'
import Link from './Link'
import Page from './Page'

function LoginRequired({ path }: { path: string }) {
  const session = useSession()
  return <Page title="Войдите в аккаунт" description="Ваши документы доступны после входа." narrow>
    {session.message && <p className="notice" role="status">{session.message}</p>}
    <div className="actions"><Link className="button button-primary" href={authPath('login', path)}>Войти</Link><Link className="button button-outline" href={authPath('register', path)}>Создать аккаунт</Link></div>
  </Page>
}

export default LoginRequired
