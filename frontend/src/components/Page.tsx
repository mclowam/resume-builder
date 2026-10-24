import type { ReactNode } from 'react'
import Link from './Link'

type Props = { title: string; description?: string; children: ReactNode; back?: { href: string; label: string }; narrow?: boolean }

function Page({ title, description, children, back, narrow }: Props) {
  return <main id="main" className={`page${narrow ? ' page-narrow' : ''}`}>
    {back && <Link className="back-link" href={back.href}>← {back.label}</Link>}
    <section className="card" aria-labelledby="page-title">
      <h1 id="page-title" tabIndex={-1}>{title}</h1>
      {description && <p className="description">{description}</p>}
      {children}
    </section>
  </main>
}

export default Page
