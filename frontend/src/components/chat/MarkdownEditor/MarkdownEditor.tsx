import { useCallback, useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import { useEditor, EditorContent, Editor } from '@tiptap/react';
import { liftListItem, splitListItem } from '@tiptap/pm/schema-list';
import { lift } from '@tiptap/pm/commands';
import { cn } from '@/lib/utils';
import { createExtensions } from './extensions';
import { MarkdownToolbar } from './MarkdownToolbar';
import './styles.css';

// Helper to get markdown from editor storage
// tiptap-markdown adds a getMarkdown method to the storage
const getMarkdownFromEditor = (editor: Editor): string => {
  const storage = editor.storage as unknown as Record<string, { getMarkdown?: () => string }>;
  return storage.markdown?.getMarkdown?.() || editor.getText();
};

export interface MarkdownEditorRef {
  focus: () => void;
  getMarkdown: () => string;
  clear: () => void;
  editor: Editor | null;
}

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  placeholder?: string;
  disabled?: boolean;
  minHeight?: number;
  maxHeight?: number;
  size?: 'default' | 'compact';
  showToolbar?: boolean;
  className?: string;
}

export const MarkdownEditor = forwardRef<MarkdownEditorRef, MarkdownEditorProps>(
  (
    {
      value,
      onChange,
      onSubmit,
      placeholder = 'Type your message...',
      disabled = false,
      minHeight = 44,
      maxHeight = 200,
      size = 'default',
      showToolbar = true,
      className,
    },
    ref
  ) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const isInternalUpdate = useRef(false);
    const isCompact = size === 'compact';

    const editor = useEditor({
      extensions: createExtensions(placeholder),
      content: value || '',
      editable: !disabled,
      editorProps: {
        attributes: {
          class: cn(
            'markdown-editor-content outline-none',
            isCompact ? 'text-sm' : 'text-base'
          ),
        },
        handleKeyDown: (view, event) => {
          // Ctrl+Enter (or Cmd+Enter on Mac) sends the message
          if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
            event.preventDefault();
            onSubmit?.();
            return true;
          }

          // Regular Enter for smart block behavior
          if (event.key === 'Enter' && !event.ctrlKey && !event.metaKey) {
            const { state } = view;
            const { selection } = state;
            const { $from } = selection;
            const currentLineText = $from.parent.textContent;
            const isCurrentBlockEmpty = currentLineText.length === 0;

            // Check if we're in a code block
            const isInCodeBlock = $from.parent.type.name === 'codeBlock';
            if (isInCodeBlock) {
              // Get text from start of code block to cursor position
              const textBeforeCursor = $from.parent.textBetween(0, $from.parentOffset);
              const textAfterCursor = $from.parent.textBetween($from.parentOffset, $from.parent.content.size);

              // Check if we're on an empty line:
              // - Text before cursor ends with newline (we just added a blank line)
              // - Text after cursor starts with newline or is empty (nothing on this line after cursor)
              const atEmptyLineStart = textBeforeCursor.endsWith('\n');
              const atLineEnd = textAfterCursor.length === 0 || textAfterCursor.startsWith('\n');
              const isOnEmptyLine = atEmptyLineStart && atLineEnd;

              if (isOnEmptyLine) {
                event.preventDefault();
                // Exit code block: remove trailing newline and create paragraph after
                const tr = state.tr;

                // Remove the trailing empty line from the code block
                const deleteFrom = $from.pos - 1;
                tr.delete(deleteFrom, $from.pos);

                // Insert a paragraph after the code block
                const blockEnd = tr.doc.resolve(tr.mapping.map($from.pos)).end();
                tr.insert(blockEnd + 1, state.schema.nodes.paragraph.create());
                // Move cursor to the new paragraph
                tr.setSelection(state.selection.constructor.near(tr.doc.resolve(blockEnd + 2)));
                view.dispatch(tr);
                return true;
              }

              // Inside code block with content on line: insert a newline
              event.preventDefault();
              view.dispatch(state.tr.insertText('\n'));
              return true;
            }

            // Check if current line is a code fence (``` or ```language) - create code block
            if (/^`{3}/.test(currentLineText.trim())) {
              event.preventDefault();
              const language = currentLineText.trim().slice(3).trim() || null;
              const tr = state.tr;
              // Replace current paragraph with a code block
              const blockStart = $from.start() - 1;
              const blockEnd = $from.end() + 1;
              const codeBlock = state.schema.nodes.codeBlock.create(
                language ? { language } : null
              );
              tr.replaceWith(blockStart, blockEnd, codeBlock);
              // Position cursor inside the code block
              tr.setSelection(state.selection.constructor.near(tr.doc.resolve(blockStart + 1)));
              view.dispatch(tr);
              return true;
            }

            // Check if we're in a heading - always exit to paragraph
            const isInHeading = $from.parent.type.name === 'heading';
            if (isInHeading) {
              event.preventDefault();

              // Split the heading first
              const tr = state.tr.split($from.pos);

              // After split, map the position to find where cursor is in new doc
              const newCursorPos = tr.mapping.map($from.pos);
              const $newCursor = tr.doc.resolve(newCursorPos);

              // Get the boundaries of the new block and convert to paragraph
              const blockStart = $newCursor.start();
              const blockEnd = $newCursor.end();
              tr.setBlockType(blockStart, blockEnd, state.schema.nodes.paragraph);

              view.dispatch(tr);
              return true;
            }

            // Check if we're in a list item
            const isInListItem = $from.node(-1)?.type.name === 'listItem';
            const listItemType = state.schema.nodes.listItem;

            if (isInListItem && listItemType) {
              if (event.shiftKey) {
                // Shift+Enter in list: multi-line within current item
                // Get text within the paragraph inside the list item
                const textBeforeCursor = $from.parent.textBetween(0, $from.parentOffset);
                const textAfterCursor = $from.parent.textBetween($from.parentOffset, $from.parent.content.size);
                const atEmptyLineStart = textBeforeCursor.endsWith('\n');
                const atLineEnd = textAfterCursor.length === 0 || textAfterCursor.startsWith('\n');
                const isOnEmptyLine = atEmptyLineStart && atLineEnd;

                if (isOnEmptyLine) {
                  // Double Shift+Enter on empty line: exit list
                  event.preventDefault();
                  // Remove the trailing newline
                  const tr = state.tr;
                  tr.delete($from.pos - 1, $from.pos);
                  view.dispatch(tr);
                  // Then lift out of list
                  liftListItem(listItemType)(view.state, view.dispatch);
                  return true;
                }

                // Insert newline within the list item (multi-line)
                event.preventDefault();
                view.dispatch(state.tr.insertText('\n'));
                return true;
              } else {
                // Regular Enter in list: new item or exit on empty
                if (isCurrentBlockEmpty) {
                  // Enter on empty list item: exit list
                  event.preventDefault();
                  liftListItem(listItemType)(state, view.dispatch);
                  return true;
                }

                // Create new list item
                event.preventDefault();
                splitListItem(listItemType)(state, view.dispatch);
                return true;
              }
            }

            // Check if we're in a blockquote
            const isInBlockquote = $from.node(-1)?.type.name === 'blockquote' ||
                                    $from.node(-2)?.type.name === 'blockquote';

            if (isInBlockquote) {
              if (isCurrentBlockEmpty) {
                // Enter/Shift+Enter on empty line in blockquote: exit
                event.preventDefault();
                if (lift(state, view.dispatch)) {
                  return true;
                }
                return true;
              }

              // Non-empty: split to create new paragraph within blockquote
              event.preventDefault();
              const tr = state.tr.split($from.pos);
              view.dispatch(tr);
              return true;
            }

            // For regular paragraphs, split to create a new block
            // This allows markdown input rules to trigger on the new line
            const isInParagraph = $from.parent.type.name === 'paragraph';
            if (isInParagraph) {
              event.preventDefault();
              const tr = state.tr.split($from.pos);
              view.dispatch(tr);
              return true;
            }
          }

          return false;
        },
      },
      onUpdate: ({ editor }) => {
        isInternalUpdate.current = true;
        const markdown = getMarkdownFromEditor(editor);
        onChange(markdown);
        // Reset flag after a tick
        setTimeout(() => {
          isInternalUpdate.current = false;
        }, 0);
      },
    });

    // Sync external value changes
    useEffect(() => {
      if (!editor || isInternalUpdate.current) return;

      const currentMarkdown = getMarkdownFromEditor(editor);
      if (value !== currentMarkdown) {
        // Preserve cursor position when possible
        const { from, to } = editor.state.selection;
        editor.commands.setContent(value || '');
        // Try to restore selection if still valid
        try {
          const maxPos = editor.state.doc.content.size;
          if (from <= maxPos && to <= maxPos) {
            editor.commands.setTextSelection({ from, to });
          }
        } catch {
          // Selection restoration failed, that's okay
        }
      }
    }, [value, editor]);

    // Update editable state
    useEffect(() => {
      if (editor) {
        editor.setEditable(!disabled);
      }
    }, [disabled, editor]);

    // Update placeholder dynamically
    useEffect(() => {
      if (editor) {
        const placeholderExtension = editor.extensionManager.extensions.find(
          (ext) => ext.name === 'placeholder'
        );
        if (placeholderExtension) {
          placeholderExtension.options.placeholder = placeholder;
          // Force re-render of placeholder
          editor.view.dispatch(editor.state.tr);
        }
      }
    }, [placeholder, editor]);

    // Auto-resize editor
    useEffect(() => {
      if (!editor || !containerRef.current) return;

      const updateHeight = () => {
        const editorElement = containerRef.current?.querySelector('.ProseMirror');
        if (editorElement) {
          const scrollHeight = (editorElement as HTMLElement).scrollHeight;
          const newHeight = Math.max(minHeight, Math.min(scrollHeight + 2, maxHeight));
          if (containerRef.current) {
            containerRef.current.style.height = `${newHeight}px`;
          }
        }
      };

      // Update height on content changes
      editor.on('update', updateHeight);
      updateHeight();

      return () => {
        editor.off('update', updateHeight);
      };
    }, [editor, minHeight, maxHeight]);

    // Expose methods via ref
    useImperativeHandle(ref, () => ({
      focus: () => editor?.commands.focus(),
      getMarkdown: () => (editor ? getMarkdownFromEditor(editor) : ''),
      clear: () => editor?.commands.clearContent(),
      editor,
    }));

    const handleFocus = useCallback(() => {
      editor?.commands.focus();
    }, [editor]);

    return (
      <div className={cn('markdown-editor-wrapper', className)}>
        {showToolbar && editor && (
          <MarkdownToolbar editor={editor} size={size} disabled={disabled} />
        )}
        <div
          ref={containerRef}
          onClick={handleFocus}
          className={cn(
            'markdown-editor',
            disabled && 'opacity-50 cursor-not-allowed',
            isCompact ? 'py-1.5 px-2' : 'py-2 px-3'
          )}
          style={{
            minHeight: `${minHeight}px`,
            maxHeight: `${maxHeight}px`,
            overflowY: 'auto',
          }}
        >
          <EditorContent editor={editor} />
        </div>
      </div>
    );
  }
);

MarkdownEditor.displayName = 'MarkdownEditor';
