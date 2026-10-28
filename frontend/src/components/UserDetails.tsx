import { Avatar, Badge, Group, Paper, Text } from '@mantine/core'
import type { Profile, User } from '../types/api'

function UserDetails({ user }: { user: Profile | User }) {
  return <>
    <Group wrap="nowrap" gap="md" mb="xl"><Avatar size={56} radius="lg" color="teal">{user.username.slice(0, 1).toUpperCase()}</Avatar><div className="resource-copy"><Text fw={650} size="lg" className="wrap-text">{user.username}</Text><Badge variant="light" mt={6} color={user.is_staff ? 'teal' : 'gray'}>{user.is_staff ? 'Сотрудник' : 'Личный аккаунт'}</Badge></div></Group>
    <Paper component="dl" className="details" radius="md">
      <div><dt>Имя пользователя</dt><dd>{user.username}</dd></div>
      <div><dt>Идентификатор</dt><dd className="identifier">{user.user_id}</dd></div>
      <div><dt>Сотрудник</dt><dd>{user.is_staff ? 'Да' : 'Нет'}</dd></div>
      {'is_active' in user && <div><dt>Аккаунт активен</dt><dd>{user.is_active ? 'Да' : 'Нет'}</dd></div>}
    </Paper>
  </>
}

export default UserDetails
