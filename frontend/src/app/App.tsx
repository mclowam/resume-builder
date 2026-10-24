import HomePage from '../pages/HomePage'
import LoginPage from '../pages/LoginPage'
import RegisterPage from '../pages/RegisterPage'
import AddResumePage from '../pages/AddResumePage'
import AddVacancyPage from '../pages/AddVacancyPage'
import Header from '../components/Header'
import LoginRequired from '../components/LoginRequired'

function App() {
  const path = window.location.pathname
  const isLoggedIn = Boolean(sessionStorage.getItem('access_token'))

  let page

  switch (path) {
    case '/login':
      page = <LoginPage />
      break
    case '/register':
      page = <RegisterPage />
      break
    case '/add-resume':
      page = isLoggedIn ? <AddResumePage /> : <LoginRequired />
      break
    case '/add-vacancy':
      page = isLoggedIn ? <AddVacancyPage /> : <LoginRequired />
      break
    default:
      page = <HomePage />
  }

  return (
    <>
      <Header />
      {page}
    </>
  )
}

export default App
