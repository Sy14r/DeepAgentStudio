import { useCallback } from 'react';
import { Editor } from '@tiptap/react';
import {
  Bold,
  Italic,
  Code,
  List,
  ListOrdered,
  Quote,
  Link as LinkIcon,
  Code2,
} from 'lucide-react';
import {
  Button,
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from '@/components/ui';
import { cn } from '@/lib/utils';

interface MarkdownToolbarProps {
  editor: Editor;
  size?: 'default' | 'compact';
  disabled?: boolean;
}

interface ToolbarButtonProps {
  icon: React.ReactNode;
  label: string;
  shortcut?: string;
  isActive?: boolean;
  onClick: () => void;
  disabled?: boolean;
  size?: 'default' | 'compact';
}

function ToolbarButton({
  icon,
  label,
  shortcut,
  isActive,
  onClick,
  disabled,
  size = 'default',
}: ToolbarButtonProps) {
  const isCompact = size === 'compact';

  // Use onMouseDown with preventDefault to prevent the button from stealing focus
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    onClick();
  };

  return (
    <TooltipProvider delayDuration={300}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onMouseDown={handleMouseDown}
            disabled={disabled}
            tabIndex={-1}
            className={cn(
              isCompact ? 'h-6 w-6 p-0' : 'h-7 w-7 p-0',
              isActive && 'bg-accent text-accent-foreground'
            )}
          >
            {icon}
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top" className="flex items-center gap-2">
          <span>{label}</span>
          {shortcut && (
            <kbd className="px-1.5 py-0.5 text-xs bg-muted rounded">
              {shortcut}
            </kbd>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function MarkdownToolbar({ editor, size = 'default', disabled = false }: MarkdownToolbarProps) {
  const isCompact = size === 'compact';
  const iconClass = isCompact ? 'h-3 w-3' : 'h-3.5 w-3.5';

  const handleBold = useCallback(() => {
    editor.chain().focus().toggleBold().run();
  }, [editor]);

  const handleItalic = useCallback(() => {
    editor.chain().focus().toggleItalic().run();
  }, [editor]);

  const handleCode = useCallback(() => {
    editor.chain().focus().toggleCode().run();
  }, [editor]);

  const handleCodeBlock = useCallback(() => {
    editor.chain().focus().toggleCodeBlock().run();
  }, [editor]);

  const handleBulletList = useCallback(() => {
    editor.chain().focus().toggleBulletList().run();
  }, [editor]);

  const handleOrderedList = useCallback(() => {
    editor.chain().focus().toggleOrderedList().run();
  }, [editor]);

  const handleBlockquote = useCallback(() => {
    editor.chain().focus().toggleBlockquote().run();
  }, [editor]);

  const handleLink = useCallback(() => {
    const previousUrl = editor.getAttributes('link').href;
    const url = window.prompt('Enter URL:', previousUrl || 'https://');

    if (url === null) {
      return; // Cancelled
    }

    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run();
      return;
    }

    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
  }, [editor]);

  return (
    <div
      className={cn(
        'flex items-center gap-0.5 px-2',
        isCompact ? 'py-0.5' : 'py-1'
      )}
    >
      <ToolbarButton
        icon={<Bold className={iconClass} />}
        label="Bold"
        shortcut="Ctrl+B"
        isActive={editor.isActive('bold')}
        onClick={handleBold}
        disabled={disabled}
        size={size}
      />
      <ToolbarButton
        icon={<Italic className={iconClass} />}
        label="Italic"
        shortcut="Ctrl+I"
        isActive={editor.isActive('italic')}
        onClick={handleItalic}
        disabled={disabled}
        size={size}
      />
      <ToolbarButton
        icon={<Code className={iconClass} />}
        label="Inline Code"
        shortcut="Ctrl+E"
        isActive={editor.isActive('code')}
        onClick={handleCode}
        disabled={disabled}
        size={size}
      />

      <div className="w-px h-4 bg-border mx-1" />

      <ToolbarButton
        icon={<Code2 className={iconClass} />}
        label="Code Block"
        isActive={editor.isActive('codeBlock')}
        onClick={handleCodeBlock}
        disabled={disabled}
        size={size}
      />
      <ToolbarButton
        icon={<List className={iconClass} />}
        label="Bullet List"
        isActive={editor.isActive('bulletList')}
        onClick={handleBulletList}
        disabled={disabled}
        size={size}
      />
      <ToolbarButton
        icon={<ListOrdered className={iconClass} />}
        label="Numbered List"
        isActive={editor.isActive('orderedList')}
        onClick={handleOrderedList}
        disabled={disabled}
        size={size}
      />

      <div className="w-px h-4 bg-border mx-1" />

      <ToolbarButton
        icon={<Quote className={iconClass} />}
        label="Blockquote"
        isActive={editor.isActive('blockquote')}
        onClick={handleBlockquote}
        disabled={disabled}
        size={size}
      />
      <ToolbarButton
        icon={<LinkIcon className={iconClass} />}
        label="Link"
        shortcut="Ctrl+K"
        isActive={editor.isActive('link')}
        onClick={handleLink}
        disabled={disabled}
        size={size}
      />
    </div>
  );
}
