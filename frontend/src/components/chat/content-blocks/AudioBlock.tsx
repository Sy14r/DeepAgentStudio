/**
 * AudioBlock component for rendering audio content with HTML5 player.
 */
import { useRef, useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Download, Volume2 } from 'lucide-react';
import type { ContentBlock } from '@/api/types';
import { useAuthStore } from '@/stores/authStore';

interface AudioBlockProps {
  block: ContentBlock;
  className?: string;
}

export function AudioBlock({ block, className }: AudioBlockProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const token = useAuthStore((state) => state.token);

  const fileName = block.file_name || 'audio';
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

  const audioUrl = getFullUrl(block.url || '');

  // Fetch audio with auth token
  useEffect(() => {
    if (block.url?.startsWith('/api/')) {
      fetch(audioUrl, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
        .then((res) => res.blob())
        .then((blob) => {
          const objectUrl = URL.createObjectURL(blob);
          setAudioSrc(objectUrl);
          setIsLoading(false);
        })
        .catch((err) => {
          console.error('Failed to load audio:', err);
          setIsLoading(false);
        });
    } else {
      setAudioSrc(audioUrl);
      setIsLoading(false);
    }

    return () => {
      if (audioSrc && audioSrc.startsWith('blob:')) {
        URL.revokeObjectURL(audioSrc);
      }
    };
  }, [block.url, audioUrl, token]);

  const handleDownload = async () => {
    try {
      const response = await fetch(audioUrl, {
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
      console.error('Failed to download audio:', error);
    }
  };

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`flex items-center gap-3 p-3 bg-muted/50 rounded-lg ${className}`}>
      <div className="flex-shrink-0">
        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
          <Volume2 className="h-5 w-5 text-primary" />
        </div>
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{fileName}</span>
          {duration && (
            <span className="text-xs text-muted-foreground">
              {formatDuration(duration)}
            </span>
          )}
        </div>

        {isLoading ? (
          <div className="h-8 mt-1 bg-muted animate-pulse rounded" />
        ) : (
          <audio
            ref={audioRef}
            src={audioSrc || audioUrl}
            controls
            className="w-full mt-1 h-8"
            preload="metadata"
          />
        )}
      </div>

      <Button
        size="icon"
        variant="ghost"
        className="flex-shrink-0"
        onClick={handleDownload}
        title="Download"
      >
        <Download className="h-4 w-4" />
      </Button>
    </div>
  );
}
