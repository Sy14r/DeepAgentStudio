/**
 * VideoBlock component for rendering video content with HTML5 player.
 */
import { useRef, useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Download, Play, Maximize } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import type { ContentBlock } from '@/api/types';
import { useAuthStore } from '@/stores/authStore';

interface VideoBlockProps {
  block: ContentBlock;
  className?: string;
}

export function VideoBlock({ block, className }: VideoBlockProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const token = useAuthStore((state) => state.token);

  const fileName = block.file_name || 'video';
  const width = block.metadata?.width as number | undefined;
  const height = block.metadata?.height as number | undefined;
  const duration = block.metadata?.duration as number | undefined;

  // Build full URL
  const getFullUrl = (url: string): string => {
    if (!url) return '';
    if (url.startsWith('/api/')) {
      const baseUrl = import.meta.env.VITE_API_URL || '';
      return `${baseUrl}${url}`;
    }
    return url;
  };

  const videoUrl = getFullUrl(block.url || '');

  // Fetch video with auth token
  useEffect(() => {
    if (block.url?.startsWith('/api/')) {
      fetch(videoUrl, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
        .then((res) => res.blob())
        .then((blob) => {
          const objectUrl = URL.createObjectURL(blob);
          setVideoSrc(objectUrl);
          setIsLoading(false);
        })
        .catch((err) => {
          console.error('Failed to load video:', err);
          setIsLoading(false);
        });
    } else {
      setVideoSrc(videoUrl);
      setIsLoading(false);
    }

    return () => {
      if (videoSrc && videoSrc.startsWith('blob:')) {
        URL.revokeObjectURL(videoSrc);
      }
    };
  }, [block.url, videoUrl, token]);

  const handleDownload = async () => {
    try {
      const response = await fetch(videoUrl, {
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
      console.error('Failed to download video:', error);
    }
  };

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`relative group ${className}`}>
      {/* Video container */}
      <div className="relative inline-block max-w-full">
        {isLoading ? (
          <div
            className="w-80 h-48 bg-muted animate-pulse rounded-lg flex items-center justify-center"
            style={width && height ? { aspectRatio: `${width}/${height}` } : undefined}
          >
            <Play className="h-8 w-8 text-muted-foreground" />
          </div>
        ) : (
          <video
            ref={videoRef}
            src={videoSrc || videoUrl}
            controls
            className="max-w-full max-h-[400px] rounded-lg"
            style={width && height ? { aspectRatio: `${width}/${height}` } : undefined}
            preload="metadata"
          />
        )}

        {/* Overlay controls */}
        <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            size="icon"
            variant="secondary"
            className="h-8 w-8"
            onClick={() => setIsFullscreen(true)}
            title="Fullscreen"
          >
            <Maximize className="h-4 w-4" />
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

      {/* Info caption */}
      <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
        <span className="font-medium">{fileName}</span>
        {duration && <span>({formatDuration(duration)})</span>}
        {width && height && <span>{width}x{height}</span>}
      </div>

      {/* Fullscreen dialog */}
      <Dialog open={isFullscreen} onOpenChange={setIsFullscreen}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] p-0 overflow-hidden bg-black">
          <DialogTitle className="sr-only">{fileName}</DialogTitle>
          <DialogDescription className="sr-only">
            Video: {fileName}
          </DialogDescription>
          <div className="relative flex items-center justify-center">
            <video
              src={videoSrc || videoUrl}
              controls
              autoPlay
              className="max-w-full max-h-[85vh]"
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
