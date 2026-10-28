import { Button, createTheme, Paper, PasswordInput, Textarea, TextInput } from '@mantine/core'

export const theme = createTheme({
  primaryColor: 'teal',
  primaryShade: 8,
  fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  headings: { fontWeight: '650', sizes: { h1: { fontSize: '2rem', lineHeight: '1.2' }, h2: { fontSize: '1.125rem', lineHeight: '1.5' } } },
  defaultRadius: 'md',
  focusRing: 'always',
  components: {
    Button: Button.extend({ defaultProps: { size: 'md' } }),
    Paper: Paper.extend({ defaultProps: { withBorder: true, radius: 'lg' } }),
    TextInput: TextInput.extend({ defaultProps: { size: 'md', withAsterisk: false } }),
    PasswordInput: PasswordInput.extend({ defaultProps: { size: 'md', withAsterisk: false } }),
    Textarea: Textarea.extend({ defaultProps: { size: 'md', withAsterisk: false } }),
  },
})
