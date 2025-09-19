import { forwardRef } from 'react';
import type { KeyboardEvent } from 'react';
import MediaCardBase from '@/app/components/MediaCard/MediaCardBase';
import type { DiscoverItem } from '@/app/lib/types';

interface TvCardProps {
  item: DiscoverItem;
  tabIndex?: number;
  onFocus?: () => void;
  onKeyDown?: (event: KeyboardEvent<HTMLDivElement>) => void;
}

const TvCard = forwardRef<HTMLDivElement, TvCardProps>((props, ref) => <MediaCardBase ref={ref} {...props} />);

TvCard.displayName = 'TvCard';

export default TvCard;
