import { getVacancies } from '../api/documents'
import { useResource } from '../app/useResource'
import { EmptyState, ErrorNotice, Loading } from '../components/Feedback'
import Link from '../components/Link'
import Page from '../components/Page'

function VacanciesPage() {
  const resource = useResource(getVacancies)
  return <Page title="Мои вакансии" description="Сохранённые тексты вакансий вашего аккаунта.">
    <div className="toolbar"><Link className="button button-primary" href="/add-vacancy">Добавить вакансию</Link><button className="button button-outline" onClick={resource.reload} disabled={resource.loading}>Обновить список</button></div>
    <ErrorNotice error={resource.error} retry={resource.reload} />
    {resource.loading && <Loading />}
    {resource.data?.length === 0 && !resource.loading && !resource.error && <EmptyState title="Пока нет вакансий" description="Сохраните полный текст первой вакансии." />}
    {!!resource.data?.length && <ul className="resource-list" aria-label="Вакансии" aria-busy={resource.loading}>{resource.data.map((vacancy) => <li className="resource-row" key={vacancy.id}><div className="resource-copy"><h2><Link href={`/my-vacancies/${vacancy.id}`}>Вакансия</Link></h2><p className="text-preview">{vacancy.text || 'Текст отсутствует'}</p></div><Link className="button button-outline" href={`/my-vacancies/${vacancy.id}`}>Открыть</Link></li>)}</ul>}
  </Page>
}

export default VacanciesPage
