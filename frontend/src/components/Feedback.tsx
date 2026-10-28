import { Alert, Button, Group, Loader, Paper, Stack, Text, ThemeIcon, Title } from '@mantine/core'
import { ApiError, errorMessage } from '../api/client'
import Icon from './Icon'
import Link from './Link'

export function ErrorNotice({ error, retry, listPath }: { error: unknown; retry?: () => void; listPath?: string }) {
  if (!error) return null
  return <Alert color="red" title={error instanceof ApiError && error.status === 404 ? '404 · Не найдено' : 'Не удалось выполнить действие'} role="alert" my="md">
    <Stack gap="sm">
      <Text size="sm">{errorMessage(error)}</Text>
      {error instanceof ApiError && error.uncertain && <Text size="sm">Сервер мог сохранить данные. {listPath ? <Link href={listPath}>Проверьте список перед повторной отправкой.</Link> : 'Проверьте результат перед повторной отправкой.'}</Text>}
      {retry && <Button variant="default" size="sm" onClick={retry} style={{ alignSelf: 'flex-start' }}>Повторить</Button>}
    </Stack>
  </Alert>
}

export function Loading({ text = 'Загрузка…' }: { text?: string }) {
  return <Group py="xl" gap="sm" role="status"><Loader size="sm" /><Text size="sm" c="dimmed">{text}</Text></Group>
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return <Paper className="empty-state" withBorder={false} bg="gray.0">
    <ThemeIcon size={52} radius="xl" variant="light" color="gray" mb="md"><Icon name="resume" size={24} /></ThemeIcon>
    <Title order={2}>{title}</Title><Text c="dimmed" size="sm" mt="xs" maw={400} mx="auto">{description}</Text>
  </Paper>
}
