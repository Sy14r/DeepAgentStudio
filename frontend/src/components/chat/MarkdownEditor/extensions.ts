import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
import { Markdown } from 'tiptap-markdown';
import { common, createLowlight } from 'lowlight';

// Create lowlight instance with common languages
// Includes: javascript, typescript, python, css, html, json, bash, sql, etc.
const lowlight = createLowlight(common);

export const createExtensions = (placeholder: string) => [
  StarterKit.configure({
    // Enable heading levels 1-3 for markdown support
    heading: {
      levels: [1, 2, 3],
    },
    // Disable default codeBlock - we use CodeBlockLowlight instead
    codeBlock: false,
    // Enable horizontal rule for --- syntax
    horizontalRule: {},
  }),
  CodeBlockLowlight.configure({
    lowlight,
    defaultLanguage: 'plaintext',
    HTMLAttributes: {
      class: 'bg-muted rounded p-3 font-mono text-sm overflow-x-auto',
    },
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
