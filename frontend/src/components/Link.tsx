import type { AnchorHTMLAttributes } from 'react'
import { navigate } from '../app/navigation'

function Link({ href = '/', onClick, ...props }: AnchorHTMLAttributes<HTMLAnchorElement>) {
  return <a {...props} href={href} onClick={(event) => {
    onClick?.(event)
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey || props.target || props.download) return
    event.preventDefault()
    navigate(href)
  }} />
}

export default Link
