import { forwardRef } from 'react';
import type { KeyboardEvent } from 'react';
import MediaCardBase from '@/app/components/MediaCard/MediaCardBase';
import type { DiscoverItem } from '@/app/lib/types';

interface MovieCardProps {
  item: DiscoverItem;
  tabIndex?: number;
  onFocus?: () => void;
  onKeyDown?: (event: KeyboardEvent<HTMLDivElement>) => void;
}

const MovieCard = forwardRef<HTMLDivElement, MovieCardProps>((props, ref) => (
  <MediaCardBase ref={ref} {...props} />
));

MovieCard.displayName = 'MovieCard';

export default MovieCard;
