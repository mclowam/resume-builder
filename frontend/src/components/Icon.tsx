type Name = 'home' | 'resume' | 'vacancy' | 'users' | 'profile' | 'arrow' | 'upload'

const paths: Record<Name, string> = {
  home: 'm3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z',
  resume: 'M14 2H5a1 1 0 0 0-1 1v18a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V8z M14 2v6h6 M8 13h8 M8 17h5',
  vacancy: 'M8 7V4h8v3 M3 7h18v14H3z M3 12h18 M10 12v3h4v-3',
  users: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M22 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75',
  profile: 'M20 21v-2a7 7 0 0 0-14 0v2 M13 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8',
  arrow: 'm9 5-7 7 7 7 M2 12h20',
  upload: 'M12 16V3 m-5 5 5-5 5 5 M3 15v6h18v-6',
}

function Icon({ name, size = 20 }: { name: Name; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>
}

export default Icon
