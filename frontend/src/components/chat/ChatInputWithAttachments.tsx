import { useState, useRef, useCallback } from 'react';
import { Button, Badge, Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui';
import { Send, Paperclip, X, FileText, Image, FileCode, File, Square } from 'lucide-react';
import { cn } from '@/lib/utils';
import { MarkdownEditor, MarkdownEditorRef } from './MarkdownEditor';

export interface Attachment {
  id: string;
  name: string;
  type: 'text' | 'image' | 'code' | 'other';
  mimeType: string;
  size: number;
  content?: string; // For text files: content, for images: base64 data URL
}

interface ChatInputWithAttachmentsProps {
  value: string;
  onChange: (value: string) => void;
  onSend: (message: string, attachments: Attachment[]) => void;
  placeholder?: string;
  disabled?: boolean;
  isLoading?: boolean;
  maxHeight?: number;
  minHeight?: number;
  className?: string;
  size?: 'default' | 'compact';
  showStopButton?: boolean;
  onStop?: () => void;
}

// File type detection
const getFileType = (mimeType: string, fileName: string): Attachment['type'] => {
  if (mimeType.startsWith('image/')) return 'image';

  const codeExtensions = ['.js', '.ts', '.tsx', '.jsx', '.py', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.sh', '.bash', '.zsh', '.ps1', '.sql', '.html', '.css', '.scss', '.sass', '.less', '.vue', '.svelte'];
  const ext = '.' + fileName.split('.').pop()?.toLowerCase();
  if (codeExtensions.includes(ext)) return 'code';

  const textTypes = ['text/', 'application/json', 'application/xml', 'application/javascript', 'application/typescript'];
  if (textTypes.some(t => mimeType.startsWith(t) || mimeType.includes(t))) return 'text';

  return 'other';
};

// Get icon for file type
const getFileIcon = (type: Attachment['type']) => {
  switch (type) {
    case 'image': return <Image className="h-3 w-3" />;
    case 'code': return <FileCode className="h-3 w-3" />;
    case 'text': return <FileText className="h-3 w-3" />;
    default: return <File className="h-3 w-3" />;
  }
};

// Format file size
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export function ChatInputWithAttachments({
  value,
  onChange,
  onSend,
  placeholder = 'Type your message... (Shift+Enter for new line)',
  disabled = false,
  isLoading = false,
  maxHeight = 200,
  minHeight = 44,
  className,
  size = 'default',
  showStopButton = false,
  onStop,
}: ChatInputWithAttachmentsProps) {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  const editorRef = useRef<MarkdownEditorRef>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Process file and create attachment
  const processFile = useCallback(async (file: File): Promise<Attachment | null> => {
    const maxSize = 10 * 1024 * 1024; // 10MB limit
    if (file.size > maxSize) {
      console.warn(`File ${file.name} exceeds 10MB limit`);
      return null;
    }

    const type = getFileType(file.type, file.name);
    const attachment: Attachment = {
      id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      name: file.name,
      type,
      mimeType: file.type || 'application/octet-stream',
      size: file.size,
    };

    // Read file content
    return new Promise((resolve) => {
      const reader = new FileReader();

      if (type === 'image') {
        reader.onload = (e) => {
          attachment.content = e.target?.result as string;
          resolve(attachment);
        };
        reader.readAsDataURL(file);
      } else if (type === 'text' || type === 'code') {
        reader.onload = (e) => {
          attachment.content = e.target?.result as string;
          resolve(attachment);
        };
        reader.readAsText(file);
      } else {
        // For other types, just store metadata
        resolve(attachment);
      }
    });
  }, []);

  // Handle file selection
  const handleFileSelect = useCallback(async (files: FileList | null) => {
    if (!files) return;

    const newAttachments: Attachment[] = [];
    for (let i = 0; i < files.length; i++) {
      const attachment = await processFile(files[i]);
      if (attachment) {
        newAttachments.push(attachment);
      }
    }

    setAttachments(prev => [...prev, ...newAttachments]);
  }, [processFile]);

  // Handle drag events
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled && !isLoading) {
      setIsDragging(true);
    }
  }, [disabled, isLoading]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (!disabled && !isLoading) {
      handleFileSelect(e.dataTransfer.files);
    }
  }, [disabled, isLoading, handleFileSelect]);

  // Remove attachment
  const removeAttachment = useCallback((id: string) => {
    setAttachments(prev => prev.filter(a => a.id !== id));
  }, []);

  // Handle send
  const handleSend = useCallback(() => {
    if (!value.trim() && attachments.length === 0) return;
    onSend(value.trim(), attachments);
    onChange('');
    setAttachments([]);
    // Clear the editor
    editorRef.current?.clear();
  }, [value, attachments, onSend, onChange]);

  const isCompact = size === 'compact';
  const buttonHeight = isCompact ? 36 : 44;
  const iconSize = isCompact ? 'h-4 w-4' : 'h-4 w-4';

  return (
    <div className={cn('space-y-2', className)}>
      {/* Attachment Preview */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 px-1">
          {attachments.map((attachment) => (
            <Badge
              key={attachment.id}
              variant="secondary"
              className="flex items-center gap-1.5 pl-2 pr-1 py-1 max-w-[200px]"
            >
              {getFileIcon(attachment.type)}
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="truncate text-xs">{attachment.name}</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{attachment.name}</p>
                    <p className="text-xs text-muted-foreground">{formatFileSize(attachment.size)}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <button
                onClick={() => removeAttachment(attachment.id)}
                className="ml-1 hover:bg-muted-foreground/20 rounded p-0.5"
                type="button"
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      {/* Input Area */}
      <div
        className={cn(
          'flex gap-2 items-end relative',
          isDragging && 'ring-2 ring-primary ring-offset-2 rounded-md'
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => handleFileSelect(e.target.files)}
          accept="image/*,.txt,.md,.json,.csv,.xml,.html,.css,.js,.ts,.tsx,.jsx,.py,.java,.c,.cpp,.h,.hpp,.cs,.go,.rs,.rb,.php,.swift,.kt,.scala,.sh,.bash,.sql"
        />

        {/* Attachment button */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => fileInputRef.current?.click()}
                disabled={disabled || isLoading}
                className={cn('shrink-0', isCompact ? 'h-[36px] w-[36px]' : 'h-[44px] w-[44px]')}
              >
                <Paperclip className={iconSize} />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Attach files (drag & drop supported)</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Markdown Editor */}
        <MarkdownEditor
          ref={editorRef}
          value={value}
          onChange={onChange}
          onSubmit={handleSend}
          placeholder={placeholder}
          disabled={disabled || isLoading}
          minHeight={minHeight}
          maxHeight={maxHeight}
          size={size}
          showToolbar={true}
          className="flex-1"
        />

        {/* Send/Stop button */}
        {showStopButton && isLoading ? (
          <Button
            size={isCompact ? 'sm' : 'default'}
            variant="destructive"
            onClick={onStop}
            className={`shrink-0 h-[${buttonHeight}px]`}
            style={{ height: `${buttonHeight}px` }}
          >
            <Square className={iconSize} />
          </Button>
        ) : (
          <Button
            size={isCompact ? 'sm' : 'default'}
            onClick={handleSend}
            disabled={(!value.trim() && attachments.length === 0) || disabled || isLoading}
            className={`shrink-0 h-[${buttonHeight}px]`}
            style={{ height: `${buttonHeight}px` }}
          >
            <Send className={iconSize} />
          </Button>
        )}
      </div>

      {/* Drag overlay hint */}
      {isDragging && (
        <div className="absolute inset-0 bg-primary/10 border-2 border-dashed border-primary rounded-md flex items-center justify-center pointer-events-none">
          <p className="text-sm font-medium text-primary">Drop files here</p>
        </div>
      )}
    </div>
  );
}
