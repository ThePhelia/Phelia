import { forwardRef } from 'react';
import type { KeyboardEvent } from 'react';
import MediaCardBase from '@/app/components/MediaCard/MediaCardBase';
import type { DiscoverItem } from '@/app/lib/types';

interface AlbumCardProps {
  item: DiscoverItem;
  tabIndex?: number;
  onFocus?: () => void;
  onKeyDown?: (event: KeyboardEvent<HTMLDivElement>) => void;
}

const AlbumCard = forwardRef<HTMLDivElement, AlbumCardProps>((props, ref) => <MediaCardBase ref={ref} {...props} />);

AlbumCard.displayName = 'AlbumCard';

export default AlbumCard;
