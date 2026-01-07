/**
 * FileBlock component for rendering generic file attachments.
 */
import { Button } from '@/components/ui/button';
import { Download, File, FileText, FileSpreadsheet, FileArchive, FileCode } from 'lucide-react';
import type { ContentBlock } from '@/api/types';
import { useAuthStore } from '@/stores/authStore';

interface FileBlockProps {
  block: ContentBlock;
  className?: string;
}

// Get appropriate icon based on file extension or mime type
function getFileIcon(fileName: string, mimeType?: string) {
  const extension = fileName.split('.').pop()?.toLowerCase() || '';
  const type = mimeType?.split('/')[1] || '';

  // Code files
  if (['js', 'ts', 'py', 'java', 'cpp', 'c', 'go', 'rs', 'rb', 'php', 'html', 'css', 'json', 'xml', 'yaml', 'yml'].includes(extension)) {
    return FileCode;
  }

  // Text/document files
  if (['txt', 'md', 'doc', 'docx', 'rtf', 'pdf'].includes(extension) || type.includes('text') || type.includes('document')) {
    return FileText;
  }

  // Spreadsheet files
  if (['csv', 'xls', 'xlsx', 'ods'].includes(extension) || type.includes('sheet') || type.includes('spreadsheet')) {
    return FileSpreadsheet;
  }

  // Archive files
  if (['zip', 'tar', 'gz', 'rar', '7z', 'bz2'].includes(extension) || type.includes('zip') || type.includes('archive')) {
    return FileArchive;
  }

  // Default file icon
  return File;
}

function formatFileSize(bytes?: number): string {
  if (!bytes) return '';

  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

export function FileBlock({ block, className }: FileBlockProps) {
  const token = useAuthStore((state) => state.token);

  const fileName = block.file_name || 'file';
  const fileSize = block.file_size;
  const mimeType = block.mime_type;

  // Build full URL
  const getFullUrl = (url: string): string => {
    if (!url) return '';
    if (url.startsWith('/api/')) {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      return `${baseUrl}${url}`;
    }
    return url;
  };

  const fileUrl = getFullUrl(block.url || '');

  const handleDownload = async () => {
    try {
      const response = await fetch(fileUrl, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const blob = await response.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Failed to download file:', error);
    }
  };

  const FileIcon = getFileIcon(fileName, mimeType);

  return (
    <div className={`flex items-center gap-3 p-3 bg-muted/50 rounded-lg border ${className}`}>
      <div className="flex-shrink-0">
        <div className="w-10 h-10 rounded bg-primary/10 flex items-center justify-center">
          <FileIcon className="h-5 w-5 text-primary" />
        </div>
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate" title={fileName}>
            {fileName}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {fileSize && <span>{formatFileSize(fileSize)}</span>}
          {mimeType && <span className="truncate" title={mimeType}>{mimeType}</span>}
        </div>
      </div>

      <Button
        size="sm"
        variant="outline"
        className="flex-shrink-0"
        onClick={handleDownload}
      >
        <Download className="h-4 w-4 mr-2" />
        Download
      </Button>
    </div>
  );
}
