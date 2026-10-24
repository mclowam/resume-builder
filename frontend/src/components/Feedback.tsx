import { ApiError, errorMessage } from '../api/client'
import Link from './Link'

export function ErrorNotice({ error, retry, listPath }: { error: unknown; retry?: () => void; listPath?: string }) {
  if (!error) return null
  return <div className="notice notice-error" role="alert">
    <p>{errorMessage(error)}</p>
    {error instanceof ApiError && error.uncertain && <p>Сервер мог сохранить данные. {listPath ? <Link href={listPath}>Проверьте список перед повторной отправкой.</Link> : 'Проверьте результат перед повторной отправкой.'}</p>}
    {retry && <button className="button button-outline" onClick={retry}>Повторить</button>}
  </div>
}

export function Loading({ text = 'Загрузка…' }: { text?: string }) {
  return <p className="loading" role="status">{text}</p>
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="empty-state"><h2>{title}</h2><p>{description}</p></div>
}
