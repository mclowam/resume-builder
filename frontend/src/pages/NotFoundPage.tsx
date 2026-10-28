import { Badge, Button, Stack } from '@mantine/core'
import Link from '../components/Link'
import Page from '../components/Page'

function NotFoundPage() {
  return <Page title="Страница не найдена" description="Проверьте адрес или вернитесь на главную." narrow><Stack align="flex-start" gap="lg"><Badge variant="light" color="gray" size="lg">404</Badge><Button component={Link} href="/">На главную</Button></Stack></Page>
}

export default NotFoundPage
