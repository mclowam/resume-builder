import { Button } from '@mantine/core'
import Link from '../components/Link'

function HomePage() {
  return <main id="main" className="page workspace"><header className="workspace-hero"><div className="hero-copy"><h1><span className="hero-strong">Ваш опыт.</span><span className="hero-light">Для <span className="hero-accent">новой роли.</span></span></h1><p>Загрузите резюме один раз. Создавайте отдельную версию под каждую вакансию.</p></div></header><div className="workspace-grid"><section className="workspace-source"><h2>Один оригинал.</h2><p>Ваш опыт и факты остаются основой каждой новой версии.</p></section><section className="workspace-editor"><h2>Следующий отклик начинается здесь.</h2><p>Добавьте вакансию, получите адаптированное резюме и проверьте результат.</p><Button component={Link} href="/register?next=%2Fworkspace">Начать работу</Button></section></div></main>
}

export default HomePage
