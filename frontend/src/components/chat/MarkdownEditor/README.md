# Markdown Editor Component

A rich WYSIWYG markdown editor built with [TipTap](https://tiptap.dev/) for the chat interface. Users can type markdown syntax inline (e.g., `**bold**`) and see it render in real-time, or use toolbar buttons. Raw markdown is sent to the backend.

## Architecture

### Core Libraries

- **TipTap** (`@tiptap/react`) - Headless editor framework built on ProseMirror
- **tiptap-markdown** - Markdown parsing and serialization
- **CodeBlockLowlight** (`@tiptap/extension-code-block-lowlight`) - Syntax highlighting for code blocks
- **lowlight** - Syntax highlighting engine (uses highlight.js grammars)

### File Structure

```
MarkdownEditor/
├── index.ts              # Barrel exports
├── MarkdownEditor.tsx    # Main editor component
├── MarkdownToolbar.tsx   # Formatting toolbar (Bold, Italic, etc.)
├── extensions.ts         # TipTap extension configuration
├── styles.css            # Editor and syntax highlighting styles
└── README.md             # This file
```

## Keyboard Behavior

| Keys | Context | Action |
|------|---------|--------|
| `Ctrl+Enter` / `Cmd+Enter` | Anywhere | Send message |
| `Enter` | Normal paragraph | Create new paragraph (allows markdown input rules) |
| `Enter` | In heading | Exit heading, create paragraph |
| `Enter` | In list | Create new list item |
| `Enter` | Empty list item | Exit list |
| `Enter` | In blockquote | Create new paragraph in blockquote |
| `Enter` | Empty blockquote line | Exit blockquote |
| `Enter` | In code block | Insert newline in code block |
| `Enter` | Empty line in code block | Exit code block |
| `Shift+Enter` | In list | Multi-line within same list item |
| `Shift+Enter` | Empty line in list | Exit list |

### Code Block Creation

Type ` ``` ` or ` ```language ` (e.g., ` ```javascript `) and press `Enter` to create a code block with optional syntax highlighting.

## Block Type Behaviors

### Headings (`# `, `## `, `### `)
- Single-line only
- `Enter` always exits to a new paragraph

### Lists (`- `, `* `, `1. `)
- `Enter` creates new list item
- `Enter` on empty item exits list
- `Shift+Enter` creates multi-line content within same item
- Double `Shift+Enter` (on empty line) exits list

### Blockquotes (`> `)
- Multi-paragraph supported
- `Enter` on empty line exits blockquote

### Code Blocks (` ``` `)
- Syntax highlighting for common languages
- `Enter` adds newlines within block
- `Enter` on empty line exits block
- Language specified after opening fence: ` ```javascript `

## Supported Languages (Syntax Highlighting)

Uses `lowlight/common` which includes:
- JavaScript / TypeScript
- Python
- HTML / CSS / SCSS
- JSON / XML / YAML
- Bash / Shell
- SQL
- Go, Rust, Java, C/C++, Ruby, PHP
- And more...

## Extensions Configuration

```typescript
// extensions.ts
const extensions = [
  StarterKit.configure({
    heading: { levels: [1, 2, 3] },
    codeBlock: false, // Disabled - using CodeBlockLowlight
    horizontalRule: {},
  }),
  CodeBlockLowlight.configure({
    lowlight,
    defaultLanguage: 'plaintext',
  }),
  Link.configure({
    openOnClick: false,
    autolink: true,
  }),
  Placeholder.configure({ ... }),
  Markdown.configure({
    html: false,
    transformCopiedText: true,
    transformPastedText: true,
  }),
];
```

## Styling

Styles are in `styles.css` using Tailwind's `@apply` directive. Key sections:

- **Container styles** - Border, focus ring, scrollbar
- **Typography** - Headings, paragraphs, lists, blockquotes
- **Code blocks** - Background, padding, overflow
- **Syntax highlighting** - Colors for different token types (keywords, strings, etc.)

Syntax highlighting colors adapt to light/dark themes using `.dark` class selectors.

## Integration

The `MarkdownEditor` is wrapped by `ChatInputWithAttachments` which adds:
- File attachment support (drag & drop)
- Action bar with attachment button and send button
- Unified container styling

### Props

```typescript
interface MarkdownEditorProps {
  value: string;              // Markdown content
  onChange: (value: string) => void;
  onSubmit?: () => void;      // Called on Ctrl+Enter
  placeholder?: string;
  disabled?: boolean;
  minHeight?: number;
  maxHeight?: number;
  size?: 'default' | 'compact';
  showToolbar?: boolean;
  className?: string;
}
```

### Ref Methods

```typescript
interface MarkdownEditorRef {
  focus: () => void;
  getMarkdown: () => string;
  clear: () => void;
  editor: Editor | null;
}
```

## Getting Markdown Output

The editor stores content as ProseMirror document structure internally. To get markdown:

```typescript
// Via ref
const markdown = editorRef.current?.getMarkdown();

// Or internally via tiptap-markdown storage
const markdown = editor.storage.markdown.getMarkdown();
```
