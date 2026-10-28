import { Alert } from '@mantine/core'
import { useCallback } from 'react'
import { getVacancy } from '../api/documents'
import { useResource } from '../app/useResource'
import { ErrorNotice, Loading } from '../components/Feedback'
import Page from '../components/Page'

function VacancyPage({ id }: { id: string }) {
  const load = useCallback((signal: AbortSignal) => getVacancy(id, signal), [id])
  const resource = useResource(load)
  return <Page title="Вакансия" description="Полный сохранённый текст." back={{ href: '/my-vacancies', label: 'Мои вакансии' }}>
    {new URLSearchParams(window.location.search).has('created') && <Alert color="teal" role="status" mb="lg">Вакансия сохранена.</Alert>}
    <ErrorNotice error={resource.error} retry={resource.reload} />
    {resource.loading && <Loading />}
    {resource.data && <div className="full-text">{resource.data.text || 'Текст отсутствует'}</div>}
  </Page>
}

export default VacancyPage
