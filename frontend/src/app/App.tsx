import { useEffect } from 'react'
import { restoreSession } from '../api/auth'
import Header from '../components/Header'
import LoginRequired from '../components/LoginRequired'
import { Loading } from '../components/Feedback'
import HomePage from '../pages/HomePage'
import LoginPage from '../pages/LoginPage'
import RegisterPage from '../pages/RegisterPage'
import AddResumePage from '../pages/AddResumePage'
import AddVacancyPage from '../pages/AddVacancyPage'
import ResumesPage from '../pages/ResumesPage'
import VacanciesPage from '../pages/VacanciesPage'
import VacancyPage from '../pages/VacancyPage'
import ProfilePage from '../pages/ProfilePage'
import UsersPage from '../pages/UsersPage'
import UserPage from '../pages/UserPage'
import NotFoundPage from '../pages/NotFoundPage'
import ForbiddenPage from '../pages/ForbiddenPage'
import { useLocation } from './navigation'
import { matchRoute } from './routes'
import { useSession } from './useSession'
import { getDraft } from './drafts'

function App() {
  const location = useLocation()
  const path = location.split('?')[0]
  const route = matchRoute(path)
  const session = useSession()

  useEffect(() => { void restoreSession() }, [])
  useEffect(() => { if (session.user) getDraft(session.user.user_id) }, [session.user])
  useEffect(() => {
    if (path === '/' || session.status === 'checking') document.title = 'Resume Builder'
    window.scrollTo(0, 0)
  }, [location, path, session.status])

  let page
  if (session.status === 'checking' && route?.path !== '/') {
    page = <main id="main" className="page"><Loading text="Проверка сессии…" /></main>
  } else if (route?.protected && session.status !== 'authenticated') {
    page = <LoginRequired path={path} />
  } else if (route?.staff && session.user?.is_staff !== true) {
    page = <ForbiddenPage />
  } else {
    switch (route?.path) {
      case '/': page = <HomePage />; break
      case '/login': page = <LoginPage />; break
      case '/register': page = <RegisterPage />; break
      case '/my-resumes': page = <ResumesPage />; break
      case '/add-resume': page = <AddResumePage userId={session.user!.user_id} />; break
      case '/my-vacancies': page = <VacanciesPage />; break
      case '/add-vacancy': page = <AddVacancyPage userId={session.user!.user_id} />; break
      case '/my-vacancies/:id': page = <VacancyPage id={route.id!} />; break
      case '/profile': page = <ProfilePage />; break
      case '/users': page = <UsersPage />; break
      case '/users/:id': page = <UserPage id={route.id!} />; break
      default: page = <NotFoundPage />
    }
  }

  return <Header path={path}><div key={`${location}:${route?.protected ? `${session.generation}:${session.user?.is_staff}` : 'public'}`}>{page}</div></Header>
}

export default App
