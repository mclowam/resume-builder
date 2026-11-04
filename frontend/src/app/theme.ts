import { Button, createTheme, Paper, PasswordInput, Textarea, TextInput } from '@mantine/core'

export const theme = createTheme({
  primaryColor: 'blue',
  primaryShade: 6,
  colors: { blue: ['#eff1ff', '#dfe4ff', '#bdc8ff', '#96a6ff', '#6c83ff', '#4d68ff', '#3454f5', '#2845d7', '#203ab9', '#1b319a'] },
  fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  headings: { fontWeight: '650', sizes: { h1: { fontSize: '2.75rem', lineHeight: '1.1' }, h2: { fontSize: '1.25rem', lineHeight: '1.4' } } },
  defaultRadius: 4,
  focusRing: 'always',
  components: {
    Button: Button.extend({ defaultProps: { size: 'md' }, styles: (_, props) => ({ root: props.variant === undefined || props.variant === 'filled' ? { backgroundColor: '#17171c', color: '#fff', fontWeight: 600 } : { fontWeight: 500 } }) }),
    Paper: Paper.extend({ defaultProps: { withBorder: false, radius: 4 } }),
    TextInput: TextInput.extend({ defaultProps: { size: 'md', withAsterisk: false } }),
    PasswordInput: PasswordInput.extend({ defaultProps: { size: 'md', withAsterisk: false } }),
    Textarea: Textarea.extend({ defaultProps: { size: 'md', withAsterisk: false } }),
  },
})
