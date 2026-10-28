import { Badge, Button, Stack } from '@mantine/core'
import Link from '../components/Link'
import Page from '../components/Page'

function ForbiddenPage() {
  return <Page title="Доступ ограничен" description="Этот раздел доступен только сотрудникам. Ваши документы и профиль по-прежнему доступны." narrow>
    <Stack align="flex-start" gap="lg">
      <Badge color="orange" variant="light" size="lg">403 · Нет доступа</Badge>
      <Button component={Link} href="/my-resumes">К моим резюме</Button>
    </Stack>
  </Page>
}

export default ForbiddenPage
