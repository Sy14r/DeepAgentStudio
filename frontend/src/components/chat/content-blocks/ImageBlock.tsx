/**
 * ImageBlock component for rendering generated images with zoom and download.
 */
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Download, ZoomIn } from 'lucide-react';
import type { ContentBlock } from '@/api/types';
import { useAuthStore } from '@/stores/authStore';

interface ImageBlockProps {
  block: ContentBlock;
  className?: string;
}

export function ImageBlock({ block, className }: ImageBlockProps) {
  const [isZoomed, setIsZoomed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const token = useAuthStore((state) => state.token);

  // Build full URL with auth token for protected endpoints
  const getFullUrl = (url: string): string => {
    if (!url) return '';

    // If it's an API URL, add auth header via fetch instead
    if (url.startsWith('/api/')) {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      return `${baseUrl}${url}`;
    }

    return url;
  };

  const imageUrl = getFullUrl(block.url || '');
  const fileName = block.file_name || 'image.png';
  const prompt = block.metadata?.prompt as string | undefined;
  const revisedPrompt = block.metadata?.revised_prompt as string | undefined;
  const width = block.metadata?.width as number | undefined;
  const height = block.metadata?.height as number | undefined;

  const handleDownload = async () => {
    try {
      const response = await fetch(imageUrl, {
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
      console.error('Failed to download image:', error);
    }
  };

  // For API images, we need to fetch with auth
  const [imageSrc, setImageSrc] = useState<string | null>(null);

  // Fetch image with auth token
  useEffect(() => {
    if (block.url?.startsWith('/api/')) {
      fetch(imageUrl, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
        .then((res) => res.blob())
        .then((blob) => {
          const objectUrl = URL.createObjectURL(blob);
          setImageSrc(objectUrl);
          setIsLoading(false);
        })
        .catch((err) => {
          console.error('Failed to load image:', err);
          setIsLoading(false);
        });
    } else {
      setImageSrc(imageUrl);
      setIsLoading(false);
    }
  }, [block.url, imageUrl, token]);

  return (
    <div className={`relative group ${className}`}>
      {/* Image container */}
      <div className="relative inline-block max-w-full">
        {isLoading ? (
          <div className="w-64 h-64 bg-muted animate-pulse rounded-lg flex items-center justify-center">
            <span className="text-muted-foreground text-sm">Loading...</span>
          </div>
        ) : (
          <img
            src={imageSrc || imageUrl}
            alt={prompt || fileName}
            className="max-w-full max-h-[400px] rounded-lg cursor-pointer transition-opacity hover:opacity-90"
            onClick={() => setIsZoomed(true)}
            style={width && height ? { aspectRatio: `${width}/${height}` } : undefined}
          />
        )}

        {/* Overlay controls */}
        <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            size="icon"
            variant="secondary"
            className="h-8 w-8"
            onClick={() => setIsZoomed(true)}
            title="Zoom"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button
            size="icon"
            variant="secondary"
            className="h-8 w-8"
            onClick={handleDownload}
            title="Download"
          >
            <Download className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Caption with prompt info */}
      {(prompt || revisedPrompt) && (
        <div className="mt-2 text-xs text-muted-foreground max-w-md">
          <p className="italic line-clamp-2" title={revisedPrompt || prompt}>
            {revisedPrompt || prompt}
          </p>
        </div>
      )}

      {/* Zoom dialog */}
      <Dialog open={isZoomed} onOpenChange={setIsZoomed}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] p-0 overflow-hidden">
          <DialogTitle className="sr-only">{fileName}</DialogTitle>
          <DialogDescription className="sr-only">
            Generated image: {prompt || fileName}
          </DialogDescription>
          <div className="relative flex items-center justify-center bg-black/90">
            <img
              src={imageSrc || imageUrl}
              alt={prompt || fileName}
              className="max-w-full max-h-[85vh] object-contain"
            />
            <div className="absolute bottom-4 right-4 flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={handleDownload}
              >
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
            </div>
          </div>
          {(prompt || revisedPrompt) && (
            <div className="p-4 bg-background border-t">
              <p className="text-sm text-muted-foreground">
                <strong>Prompt:</strong> {revisedPrompt || prompt}
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
