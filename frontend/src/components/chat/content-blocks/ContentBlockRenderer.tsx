/**
 * ContentBlockRenderer - Main dispatcher for rendering multimodal content blocks.
 *
 * Routes content blocks to the appropriate type-specific renderer based on
 * the block type (text, image, audio, video, file).
 */
import type { ContentBlock } from '@/api/types';
import { TextBlock } from './TextBlock';
import { ImageBlock } from './ImageBlock';
import { AudioBlock } from './AudioBlock';
import { VideoBlock } from './VideoBlock';
import { FileBlock } from './FileBlock';

interface ContentBlockRendererProps {
  block: ContentBlock;
  className?: string;
}

export function ContentBlockRenderer({ block, className }: ContentBlockRendererProps) {
  switch (block.type) {
    case 'text':
      return <TextBlock text={block.text || ''} className={className} />;

    case 'image':
      return <ImageBlock block={block} className={className} />;

    case 'audio':
      return <AudioBlock block={block} className={className} />;

    case 'video':
      return <VideoBlock block={block} className={className} />;

    case 'file':
      return <FileBlock block={block} className={className} />;

    default:
      // Fallback for unknown types - render as file download
      console.warn('Unknown content block type:', block.type);
      return <FileBlock block={block} className={className} />;
  }
}

/**
 * Render a list of content blocks with appropriate spacing.
 */
interface ContentBlocksProps {
  blocks: ContentBlock[];
  className?: string;
}

export function ContentBlocks({ blocks, className }: ContentBlocksProps) {
  if (!blocks || blocks.length === 0) {
    return null;
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {blocks.map((block, index) => (
        <ContentBlockRenderer key={index} block={block} />
      ))}
    </div>
  );
}
