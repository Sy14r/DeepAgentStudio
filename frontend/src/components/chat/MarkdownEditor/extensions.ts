import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import { Markdown } from 'tiptap-markdown';

export const createExtensions = (placeholder: string) => [
  StarterKit.configure({
    // Enable heading levels 1-3 for markdown support
    heading: {
      levels: [1, 2, 3],
    },
    // Code block with language support
    codeBlock: {
      HTMLAttributes: {
        class: 'bg-muted rounded p-3 font-mono text-sm',
      },
    },
    // Enable horizontal rule for --- syntax
    horizontalRule: {},
  }),
  Link.configure({
    openOnClick: false,
    autolink: true,
    HTMLAttributes: {
      class: 'text-primary underline cursor-pointer',
    },
  }),
  Placeholder.configure({
    placeholder,
    emptyEditorClass: 'is-editor-empty',
  }),
  Markdown.configure({
    html: false,
    transformCopiedText: true,
    transformPastedText: true,
  }),
];
