import type { Profile, User } from '../types/api'

function UserDetails({ user }: { user: Profile | User }) {
  return <dl className="details"><div><dt>Имя пользователя</dt><dd>{user.username}</dd></div><div><dt>Идентификатор</dt><dd>{user.user_id}</dd></div><div><dt>Сотрудник</dt><dd>{user.is_staff ? 'Да' : 'Нет'}</dd></div>{'is_active' in user && <div><dt>Аккаунт активен</dt><dd>{user.is_active ? 'Да' : 'Нет'}</dd></div>}</dl>
}

export default UserDetails
