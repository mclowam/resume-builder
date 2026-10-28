import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { Anchor, Paper, Stack, Text, Title } from '@mantine/core'
import Icon from './Icon'
import Link from './Link'

type Props = { title: string; description?: string; children: ReactNode; back?: { href: string; label: string }; narrow?: boolean }

function Page({ title, description, children, back, narrow }: Props) {
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    document.title = `${title} — Resume Builder`
    heading.current?.focus()
  }, [title])
  return <main id="main" className={`page${narrow ? ' page-narrow' : ''}`}>
    {back && <Anchor component={Link} className="back-link" aria-label={`Назад: ${back.label}`} href={back.href}><Icon name="arrow" size={16} />{back.label}</Anchor>}
    <Stack gap="xl">
      <header className="page-heading"><Title ref={heading} order={1} id="page-title" tabIndex={-1}>{title}</Title>{description && <Text c="dimmed" mt="sm">{description}</Text>}</header>
      <Paper component="section" className="page-panel" aria-labelledby="page-title">{children}</Paper>
    </Stack>
  </main>
}

export default Page
