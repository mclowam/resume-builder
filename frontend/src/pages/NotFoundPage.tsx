import Link from '../components/Link'
import Page from '../components/Page'

function NotFoundPage() {
  return <Page title="Страница не найдена" description="Проверьте адрес или вернитесь на главную." narrow><Link className="button button-primary" href="/">На главную</Link></Page>
}

export default NotFoundPage
